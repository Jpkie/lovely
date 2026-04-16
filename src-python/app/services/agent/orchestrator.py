"""Agent Orchestrator — 编排全流程的总导演

职责:
  - 持有 skill_registry / tool_registry / planner / executor
  - run(): 解析技能 → 规划 → 动态构建步骤 → 执行 → 组装报告

执行流程:
  1. _resolve_skills: 确定候选 skill 列表（用户指定 / 关键词匹配 / 模糊搜索）
  2. _build_context: 构建 SSH 执行上下文
  3. planner.plan_calls(): 输出 PlannerOutput(calls=[SkillCall(skill, args)])
  4. _calls_to_plan(): 对每个 call 调用 skill.build_steps(args, ctx) → Plan
  5. executor.execute_plan(): 逐步执行（支持失败重规划）
  6. _assemble_report(): 组装 FinalReport / traces / structured_output

回退链:
  planner 无 plan_calls 接口 → 回退到 plan()
  planner 返回空 calls → 回退到固定 steps 模式
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid

from .schemas import (
    AgentRequest,
    AgentResponse,
    AgentExecutionTrace,
    AgentFinalResponse,
    Plan,
    PlanStep,
)
from .skills import get_default_skill_registry, SkillRegistry
from .planner import (
    BasePlanner,
    PlannerConfig,
    PlannerOutput,
    SkillCall,
    create_planner,
    RuleBasedPlanner,
)
from .executor import Executor, ExecutionResult, ExecutionStatus, StepExecution
from .tool_registry import ToolRegistry, get_default_registry
from .context_builder import (
    HostSummaryBuilder,
    PageSummaryBuilder,
    HostSummaryContext,
    PageSummaryContext,
)


# ────────────────── 数据模型 ──────────────────


class OrchestratorStatus(str, Enum):
    IDLE = "idle"
    PARSING = "parsing"
    PLANNING = "planning"
    EXECUTING = "executing"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"


class StructuredResult(BaseModel):
    """单个 Skill 的结构化执行结果"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    skill_name: str
    summary: str = ""
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    risk_level: str = "unknown"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FinalReport(BaseModel):
    """Agent 最终报告 — 对外统一输出格式"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str
    task: str
    status: str = "running"
    skill_name: Optional[str] = None
    plan: Optional[Dict[str, Any]] = None
    traces: List[Dict[str, Any]] = Field(default_factory=list)
    final: Optional[Dict[str, Any]] = None
    skill_results: List[StructuredResult] = Field(default_factory=list)
    raw_summary: str = ""
    structured_output: Dict[str, Any] = Field(default_factory=dict)
    total_duration_ms: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # 自动修复扩展字段
    environment: Optional[Dict[str, Any]] = None
    fixed_items: List[str] = Field(default_factory=list)
    unfixed_items: List[str] = Field(default_factory=list)
    blocked_items: List[str] = Field(default_factory=list)
    replan_count: int = 0
    final_status: Optional[str] = None


# ────────────────── 核心编排器 ──────────────────


class AgentOrchestrator:
    """Agent 编排器 — 串起「解析→规划→构建→执行→报告」全流程"""

    def __init__(
        self,
        skill_registry: Optional[SkillRegistry] = None,
        tool_registry: Optional[ToolRegistry] = None,
        planner_config: Optional[PlannerConfig] = None,
    ):
        self.skill_registry = skill_registry or get_default_skill_registry()
        self.tool_registry = tool_registry or get_default_registry()
        self.planner: BasePlanner = create_planner(planner_config or PlannerConfig())
        self.executor = Executor(self.tool_registry)

    # ─────────────── 阶段1：技能解析 ───────────────

    async def _resolve_skills(self, request: AgentRequest) -> List[Any]:
        """确定本次任务要使用的候选 Skill 列表

        优先级：
          1. 用户显式指定的 skills 列表
          2. 注册表的模糊匹配结果
          3. 规则规划器的关键词匹配
          4. 取注册表中第一个 skill 作为兜底
        """
        matched_skills: List[Any] = []

        # 路径1：用户显式指定
        if request.skills:
            for name in request.skills:
                skill = self.skill_registry.get(name)
                if skill:
                    matched_skills.append(skill)

        # 路径2：注册表模糊匹配
        if not matched_skills:
            definitions = self.skill_registry.match_skills(request.task)
            for defn in definitions[:3]:  # 最多取前 3 个匹配
                skill = self.skill_registry.get(defn.name)
                if skill:
                    matched_skills.append(skill)

        # 路径3：规则规划器关键词兜底匹配
        if not matched_skills:
            rule_planner = RuleBasedPlanner()
            matches = rule_planner._match_skill_by_keywords(request.task)
            for match in matches:
                skill = self.skill_registry.get(match.skill_name)
                if skill:
                    matched_skills.append(skill)

        # 路径4：终极兜底
        if not matched_skills:
            all_defs = self.skill_registry.list_skills()
            if all_defs:
                fallback = self.skill_registry.get(all_defs[0].name)
                if fallback:
                    matched_skills.append(fallback)

        return matched_skills

    # ─────────────── 阶段2：上下文构建 ───────────────

    def _build_context(self, request: AgentRequest) -> Dict[str, Any]:
        """构建执行上下文，确保基础依赖可用"""
        context = dict(request.context)

        if "ssh_manager" not in context:
            from app.services.ssh_manager import SSHManager
            context["ssh_manager"] = SSHManager()

        return context

    # ─────────────── 阶段3：Calls → Plan 转换 ───────────────

    @staticmethod
    def _calls_to_plan(
        output: PlannerOutput,
        request: AgentRequest,
        available_skills: List[Any],
        context: Dict[str, Any],
    ) -> Plan:
        """核心辅助方法：将 PlannerOutput 的 SkillCall 列表通过 build_steps 展开为 Plan

        这是新旧架构的桥梁 —— Planner 只负责「选哪个 skill + 传什么参数」，
        具体执行步骤由每个 Skill 通过 build_steps(args, context) 自行决定。

        Args:
            output: Planner 输出的带参数调用列表
            request: 原始请求（用于填充 Plan.request_id）
            available_skills: 可用的 Skill 实例列表
            context: 执行上下文

        Returns:
            包含动态生成步骤的 Plan 对象
        """
        skill_map = {s.name: s for s in available_skills}
        steps: List[PlanStep] = []
        step_number = 1

        for call in output.calls:
            skill_obj = skill_map.get(call.skill)
            if not skill_obj:
                continue

            # 核心：让 Skill 根据提取的参数自行决定执行哪些步骤
            dynamic_steps = skill_obj.build_steps(call.args, context)

            for skill_step in dynamic_steps:
                steps.append(PlanStep(
                    id=skill_step.id,
                    step_number=step_number,
                    description=f"[{skill_obj.name}] {skill_step.name}: {skill_step.description}",
                    skill_id=skill_obj.name,
                    tool_name=skill_step.tool_name,
                    parameters=skill_step.parameters,
                    status="pending",
                ))
                step_number += 1

        return Plan(
            id=str(uuid.uuid4()),
            request_id=request.id,
            steps=steps,
            status="planned",
        )

    @staticmethod
    def _fallback_plan_from_skills(
        request: AgentRequest,
        skills: List[Any],
        context: Dict[str, Any],
    ) -> Plan:
        """回退方案：当 planner 未返回有效 calls 时，直接从 skill 固定 steps 构建 Plan

        这保证了即使 planner 失败或返回空结果，
        orchestrator 仍能基于已匹配的 skills 生成可执行的 Plan。
        """
        steps: List[PlanStep] = []
        step_number = 1

        for skill in skills:
            # 使用空 args 调用 build_steps（大多数 skill 会返回默认固定步骤）
            dynamic_steps = skill.build_steps({}, context)

            for skill_step in dynamic_steps:
                steps.append(PlanStep(
                    id=skill_step.id,
                    step_number=step_number,
                    description=f"[{skill.name}] {skill_step.name}: {skill_step.description}",
                    skill_id=skill.name,
                    tool_name=skill_step.tool_name,
                    parameters=skill_step.parameters,
                    status="pending",
                ))
                step_number += 1

        return Plan(
            id=str(uuid.uuid4()),
            request_id=request.id,
            steps=steps,
            status="planned",
        )

    @staticmethod
    def _serialize_plan(plan: Optional[Plan]) -> Optional[Dict[str, Any]]:
        """将 Plan 序列化为字典（用于写入 report.plan）"""
        if plan is None or not hasattr(plan, "steps"):
            return None
        return {
            "id": plan.id,
            "request_id": plan.request_id,
            "steps": [
                {
                    "id": s.id,
                    "step_number": s.step_number,
                    "description": s.description,
                    "skill_id": s.skill_id,
                    "tool_name": s.tool_name,
                    "parameters": s.parameters,
                    "status": s.status,
                }
                for s in plan.steps
            ],
            "status": plan.status,
        }

    # ─────────────── 阶段4+5：执行 + 报告组装 ───────────────

    async def _assemble_report(
        self,
        request: AgentRequest,
        execution_result: ExecutionResult,
        report: FinalReport,
        skills: List[Any],
        is_auto_remediation: bool,
        max_replan_attempts: int,
        replan_count: int,
    ) -> FinalReport:
        """组装最终报告（execution_result 由调用方传入，此处只做聚合和格式化）"""

        # ── 4a: 按 Skill 分组结构化结果 ──
        skill_results: List[StructuredResult] = []

        for skill in skills:
            related_executions = [
                s
                for s in execution_result.step_executions
                if s.tool_name.startswith("detect_")
                or s.tool_name
                in [
                    "hostname",
                    "uptime",
                    "uname",
                    "memory_info",
                    "disk_info",
                    "network_info",
                ]
            ]

            structured_result = StructuredResult(
                skill_name=skill.name,
                summary=self.executor.generate_summary(execution_result, {}),
                findings=self._extract_findings_from_execution(execution_result, skill.name),
                recommendations=self._extract_recommendations_from_results(execution_result),
                risk_level=self._determine_risk_level(execution_result),
                metadata={"skill": skill.name},
            )
            skill_results.append(structured_result)

        report.skill_results = skill_results
        report.structured_output = execution_result.structured_output
        report.total_duration_ms = execution_result.total_duration_ms
        report.replan_count = replan_count

        # ── 4b: 构建 traces ──
        traces = self._build_traces(execution_result)
        report.traces = traces

        # ── 4c: 汇总风险、建议、证据 ──
        all_rec: List[str] = []
        all_risks: List[str] = []
        all_commands: List[str] = []
        all_evidence: List[Dict[str, Any]] = []
        fixed_items: List[str] = []
        unfixed_items: List[str] = []
        blocked_items: List[str] = []

        for sr in skill_results:
            all_rec.extend(sr.recommendations)
            if sr.risk_level == "high":
                all_risks.append(f"高风险: {sr.skill_name}")
            elif sr.risk_level == "medium":
                all_risks.append(f"中风险: {sr.skill_name}")
            for finding in sr.findings:
                all_evidence.append(finding)

        # ── 4d: 自动修复专项处理 ──
        if is_auto_remediation:
            exec_ctx = self._build_context(request)
            env_info, fixed_items, unfixed_items, blocked_items = \
                self._handle_remediation_classification(
                    execution_result, exec_ctx,
                )
            if env_info:
                report.environment = env_info

        report.fixed_items = fixed_items
        report.unfixed_items = unfixed_items
        report.blocked_items = blocked_items

        # ── 4e: final 字段与 raw_summary ──
        report.final = {
            "summary": self.executor.generate_summary(execution_result, {}),
            "evidence": all_evidence,
            "risks": all_risks,
            "recommendations": all_rec[:10],
            "commands": all_commands,
            "next_actions": ["持续监控系统状态", "定期执行安全审计"],
            "fixed_items": fixed_items,
            "unfixed_items": unfixed_items,
            "blocked_items": blocked_items,
        }

        report.raw_summary = self._generate_final_summary(request, execution_result, skill_results)

        # ── 4f: structured_output 详细化 ──
        report.structured_output = self._build_structured_output(
            request, execution_result, replan_count, skill_results,
        )

        # ── 4g: 最终状态判定 ──
        self._determine_final_status(
            report, execution_result, is_auto_remediation,
            max_replan_attempts, replan_count,
        )

        return report

    # ─────────────── 主入口 ───────────────

    async def run(self, request: AgentRequest) -> FinalReport:
        """编排主流程：解析 → 规划 → 构建计划 → 执行 → 报告"""
        report = FinalReport(
            request_id=request.id,
            task=request.task,
            status="running",
        )

        # 阶段1：确定候选 skills
        skills = await self._resolve_skills(request)
        if not skills:
            report.status = "failed"
            report.raw_summary = "未找到匹配 skill，请尝试其他任务描述"
            return report

        primary_skill_name = skills[0].name
        report.skill_name = primary_skill_name

        # 阶段2：构建上下文
        context = self._build_context(request)

        # 阶段3：获取规划输出并转换为 Plan
        is_auto_remediation = primary_skill_name == "auto_remediation"
        max_replan_attempts = (
            context.get("max_replan_attempts", 2) if is_auto_remediation else 0
        )

        plan = await self._obtain_plan(request, skills, context)

        report.plan = self._serialize_plan(plan)

        # 如果规划后仍无步骤
        if not plan.steps:
            report.status = "failed"
            report.raw_summary = "规划未产生任何可执行步骤"
            return report

        # 阶段4：执行
        execution_result = await self.executor.execute_plan(
            plan, request, context, max_replan_attempts=max_replan_attempts,
        )
        replan_count = getattr(execution_result, "replan_count", 0)

        # 阶段5：组装报告
        return await self._assemble_report(
            request, execution_result, report, skills,
            is_auto_remediation, max_replan_attempts, replan_count,
        )

    # ─────────────── 计划获取（含回退） ───────────────

    async def _obtain_plan(
        self,
        request: AgentRequest,
        skills: List[Any],
        context: Dict[str, Any],
    ) -> Plan:
        """获取执行 Plan，包含完整回退链

        回退顺序:
          1. planner.plan_calls() → _calls_to_plan()   [新版标准路径]
          2. planner.plan()                               [兼容旧版接口]
          3. _fallback_plan_from_skills()                  [纯兜底]
        """

        # ── 路径1：尝试新版 plan_calls 接口 ──
        try:
            planner_output: PlannerOutput = await self.planner.plan_calls(
                request, skills, context,
            )
        except (AttributeError, TypeError):
            # planner 不支持 plan_calls → 走路径2
            pass
        else:
            # 有有效 calls → 正常转换
            if planner_output and planner_output.calls:
                return self._calls_to_plan(planner_output, request, skills, context)

            # planner 返回空 calls → 回退到固定步骤模式
            return self._fallback_plan_from_skills(request, skills, context)

        # ── 路径2：旧版 plan 接口 ──
        try:
            legacy_plan = await self.planner.plan(request, skills, context)
            if legacy_plan and legacy_plan.steps:
                return legacy_plan
        except Exception:
            pass

        # ── 路径3：纯兜底 ──
        return self._fallback_plan_from_skills(request, skills, context)

    # ─────────────── 报告构建子方法 ───────────────

    def _extract_findings_from_execution(
        self,
        execution_result: ExecutionResult,
        skill_name: str,
    ) -> List[Dict[str, Any]]:
        """从执行结果中提取结构化发现项"""
        findings: List[Dict[str, Any]] = []
        for step_exec in execution_result.step_executions:
            if not (step_exec.result and step_exec.result.output):
                continue

            output = step_exec.result.output
            if isinstance(output, dict):
                findings.append({"tool": step_exec.tool_name, "data": output})
            elif isinstance(output, list):
                for item in output:
                    if isinstance(item, dict):
                        findings.append({"tool": step_exec.tool_name, "data": item})
        return findings

    def _extract_recommendations_from_results(
        self, execution_result: ExecutionResult,
    ) -> List[str]:
        """根据工具执行结果的 risk_level 生成建议"""
        recs: List[str] = []
        for step_exec in execution_result.step_executions:
            if not (step_exec.result and step_exec.result.metadata):
                continue
            rl = step_exec.result.metadata.get("risk_level", "")
            tool = step_exec.tool_name
            if rl == "high":
                recs.append(f"检测到 {tool} 高风险问题，请立即处理")
            elif rl == "medium":
                recs.append(f"检测到 {tool} 中风险问题，建议尽快处理")
        if not recs:
            recs.append("未发现高风险问题，建议保持当前安全配置")
        return recs

    def _determine_risk_level(self, execution_result: ExecutionResult) -> str:
        """综合所有步骤的最高风险等级"""
        high = medium = 0
        for se in execution_result.step_executions:
            if se.result and se.result.metadata:
                r = se.result.metadata.get("risk_level", "low")
                if r == "high":
                    high += 1
                elif r == "medium":
                    medium += 1
        if high > 0:
            return "high"
        if medium > 0:
            return "medium"
        return "low"

    def _generate_final_summary(
        self,
        request: AgentRequest,
        execution_result: ExecutionResult,
        skill_results: List[StructuredResult],
    ) -> str:
        """生成人类可读的 Markdown 摘要"""
        lines = ["# Agent 执行报告\n"]
        lines.append(f"**任务**: {request.task}\n")
        lines.append(f"**状态**: {execution_result.status.value}\n")
        lines.append(f"**总耗时**: {execution_result.total_duration_ms}ms\n")

        if skill_results:
            lines.append("\n## Skill 执行结果\n")
            for sr in skill_results:
                lines.append(f"### {sr.skill_name}\n")
                lines.append(f"- 风险等级: {sr.risk_level}\n")
                lines.append(f"- 摘要: {sr.summary}\n")
                if sr.recommendations:
                    lines.append("- 建议:")
                    for r in sr.recommendations:
                        lines.append(f"  - {r}")
                lines.append("")

        lines.append("\n## 结构化输出\n")
        struct = execution_result.structured_output
        summary = struct.get("summary", {})
        lines.append(f"- 总步骤: {summary.get('total_steps', 0)}")
        lines.append(f"- 成功: {summary.get('successful_steps', 0)}")
        lines.append(f"- 失败: {summary.get('failed_steps', 0)}")

        return "\n".join(lines)

    def _build_traces(self, execution_result: ExecutionResult) -> List[Dict[str, Any]]:
        """将每步执行记录转为 trace 条目"""
        traces: List[Dict[str, Any]] = []
        for se in execution_result.step_executions:
            output_preview = None
            tool_result_summary = None
            verification_passed = None
            error_type = None

            if se.result and se.result.output:
                out_str = str(se.result.output)
                output_preview = out_str[:200] + ("..." if len(out_str) > 200 else "")
                tool_result_summary = out_str[:500] if len(out_str) > 500 else out_str

            if se.result and se.result.metadata:
                verification_passed = se.result.metadata.get("verification_passed")
                error_type = se.result.metadata.get("error_type")

            traces.append({
                "id": str(uuid.uuid4()),
                "plan_id": execution_result.plan_id,
                "step_id": se.id,
                "step_number": se.step_number,
                "tool_name": se.tool_name,
                "tool_result_summary": tool_result_summary,
                "output_preview": output_preview,
                "status": se.status.value if hasattr(se.status, "value") else str(se.status),
                "started_at": se.started_at.isoformat() if se.started_at else None,
                "completed_at": se.completed_at.isoformat() if se.completed_at else None,
                "duration_ms": se.duration_ms,
                "success": se.status == ExecutionStatus.COMPLETED,
                "error": se.error,
                "verification_passed": verification_passed,
                "error_type": error_type,
            })
        return traces

    def _handle_remediation_classification(
        self,
        execution_result: ExecutionResult,
        exec_ctx: Dict[str, Any],
    ) -> tuple:
        """自动修复场景：分类修复结果为 fixed/unfixed/blocked

        Returns:
            (env_info_dict, fixed_list, unfixed_list, blocked_list)
        """
        env_info = None
        fixed_items: List[str] = []
        unfixed_items: List[str] = []
        blocked_items: List[str] = []

        findings = exec_ctx.get("all_findings", [])
        successful_tools = {
            s.tool_name
            for s in execution_result.step_executions
            if s.status == ExecutionStatus.COMPLETED
        }
        failed_tools = {
            s.tool_name
            for s in execution_result.step_executions
            if s.status == ExecutionStatus.FAILED
        }

        for finding in findings:
            title = finding.get("title", "")
            severity = finding.get("severity", "")

            if any(f"patch_{c}" in successful_tools for c in ("pam", "ssh", "fw", "user")):
                fixed_items.append(f"[{severity}] {title}")
            elif any(f"patch_{c}" in failed_tools for c in ("pam", "ssh", "fw", "user")):
                fail_step = next(
                    (s for s in execution_result.step_executions
                     if s.tool_name.startswith("patch_") and s.status == ExecutionStatus.FAILED),
                    None,
                )
                if (
                    fail_step
                    and fail_step.result
                    and fail_step.result.metadata.get("error_type") == "permission_denied"
                ):
                    blocked_items.append(f"[{severity}] {title} (权限不足)")
                else:
                    unfixed_items.append(f"[{severity}] {title}")

        env_info_raw = exec_ctx.get("env_info")
        if env_info_raw:
            env_info = {
                "os_family": env_info_raw.os_family,
                "distribution": env_info_raw.distribution,
                "version": env_info_raw.version,
                "package_manager": env_info_raw.package_manager,
                "init_system": env_info_raw.init_system,
                "sudo_available": env_info_raw.sudo_available,
                "current_user": env_info_raw.current_user,
            }

        return env_info, fixed_items, unfixed_items, blocked_items

    def _build_structured_output(
        self,
        request: AgentRequest,
        execution_result: ExecutionResult,
        replan_count: int,
        skill_results: List[StructuredResult],
    ) -> Dict[str, Any]:
        """构建详细的 structured_output 字典"""
        failed_count = sum(
            1 for s in execution_result.step_executions
            if s.status == ExecutionStatus.FAILED
        )
        total = len(execution_result.step_executions)

        return {
            "execution_id": execution_result.id,
            "plan_id": execution_result.plan_id,
            "request_id": request.id,
            "status": execution_result.status.value,
            "summary": {
                "total_steps": total,
                "successful_steps": total - failed_count,
                "failed_steps": failed_count,
                "replanned_steps": replan_count,
                "total_duration_ms": execution_result.total_duration_ms,
            },
            "environment": getattr(self, '_last_env_info', None),  # 由 _assemble_report 填充
            "skill_results": [
                {
                    "skill_name": sr.skill_name,
                    "risk_level": sr.risk_level,
                    "recommendations": sr.recommendations,
                    "findings_count": len(sr.findings),
                }
                for sr in skill_results
            ],
            "steps": [
                {
                    "step_id": s.id,
                    "step_number": s.step_number,
                    "tool_name": s.tool_name,
                    "title": s.description,
                    "status": s.status.value,
                    "duration_ms": s.duration_ms,
                    "error": s.error,
                    "error_type": s.result.metadata.get("error_type")
                    if s.result and s.result.metadata else None,
                    "verification_passed": s.result.metadata.get("verification_passed")
                    if s.result and s.result.metadata else None,
                    "replan_count": 0,
                }
                for s in execution_result.step_executions
            ],
        }

    def _determine_final_status(
        self,
        report: FinalReport,
        execution_result: ExecutionResult,
        is_auto_remediation: bool,
        max_replan_attempts: int,
        replan_count: int,
    ):
        """根据执行结果设定报告的最终状态"""
        failed_count = sum(
            1 for s in execution_result.step_executions
            if s.status == ExecutionStatus.FAILED
        )
        total = len(execution_result.step_executions)

        if execution_result.status == ExecutionStatus.COMPLETED:
            if failed_count > 0 and total > 0:
                if failed_count == total:
                    report.status = "failed"
                    report.final_status = "failed"
                else:
                    report.status = "partially_completed"
                    report.final_status = "partially_completed"
            else:
                report.status = "completed"
                report.final_status = "completed"

        elif execution_result.status == ExecutionStatus.FAILED:
            if replan_count >= max_replan_attempts and max_replan_attempts > 0:
                report.status = "failed_after_replan"
                report.final_status = "failed_after_replan"
            else:
                report.status = "failed"
                report.final_status = "failed"
        else:
            report.status = execution_result.status.value
            report.final_status = execution_result.status.value

        # 权限阻塞检测
        local_env = report.environment
        if (
            is_auto_remediation
            and local_env
            and not local_env.get("sudo_available", True)
            and local_env.get("current_user") != "root"
        ):
            report.status = "blocked_by_permission"
            report.final_status = "blocked_by_permission"


# ────────────────── 便捷函数 ──────────────────


async def run_agent_task(
    task: str,
    context: Optional[Dict[str, Any]] = None,
    skills: Optional[List[str]] = None,
    max_steps: int = 10,
) -> FinalReport:
    """便捷入口：一行代码运行 Agent 任务"""
    request = AgentRequest(
        task=task,
        context=context or {},
        skills=skills or [],
        max_steps=max_steps,
    )
    orchestrator = AgentOrchestrator()
    return await orchestrator.run(request)
