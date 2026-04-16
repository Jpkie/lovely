"""Agent Orchestrator - 串起全流程

职责:
  - AgentOrchestrator 是 Agent 执行的总导演
  - 持有 skill_registry、tool_registry、planner、executor
  - run() 方法完成: 解析技能 → 生成计划 → 执行计划 → 收集结果

新版执行流程（run 方法）:
  1. _parse_skills: 解析任务匹配的 skills
  2. _build_context: 构建 SSH 执行上下文
  3. planner.plan_calls(): 输出 PlannerOutput(calls=[SkillCall(skill, args)])
  4. 对每个 call 调用 skill.build_steps(args, context) 动态生成 PlanStep
  5. executor.execute_plan(): 按计划执行工具链（支持失败重规划）
  6. 组装 FinalReport: plan / traces / final / raw_summary

tool_registry 注入:
  - /agent/run 传入 runtime_registry（合并了 internal + MCP）
  - 如果未传入，默认使用 get_default_registry()

自动修复增强:
  - 支持 auto_remediation skill 的环境识别
  - 支持失败重规划（有限次，最多 max_replan_attempts）
  - 支持失败分类（permission_denied, file_not_found 等）
  - 支持修复验证
  - 支持生成结构化修复报告（fixed/unfixed/blocked items）
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
)
from .skills import get_default_skill_registry, SkillRegistry
from .planner import BasePlanner, PlannerConfig, create_planner, PlannerOutput
from .executor import Executor, ExecutionResult, ExecutionStatus, StepExecution
from .tool_registry import ToolRegistry, get_default_registry
from .context_builder import (
    HostSummaryBuilder,
    PageSummaryBuilder,
    HostSummaryContext,
    PageSummaryContext,
)


class OrchestratorStatus(str, Enum):
    IDLE = "idle"
    PARSING = "parsing"
    PLANNING = "planning"
    EXECUTING = "executing"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"


class StructuredResult(BaseModel):
    """结构化结果"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    skill_name: str
    summary: str
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    risk_level: str = "unknown"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FinalReport(BaseModel):
    """最终报告"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str
    task: str
    status: str
    skill_name: Optional[str] = None
    plan: Optional[Dict[str, Any]] = None
    traces: List[Dict[str, Any]] = Field(default_factory=list)
    final: Optional[Dict[str, Any]] = None
    skill_results: List[StructuredResult] = Field(default_factory=list)
    raw_summary: str = ""
    structured_output: Dict[str, Any] = Field(default_factory=dict)
    total_duration_ms: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    environment: Optional[Dict[str, Any]] = None
    fixed_items: List[str] = Field(default_factory=list)
    unfixed_items: List[str] = Field(default_factory=list)
    blocked_items: List[str] = Field(default_factory=list)
    replan_count: int = 0
    final_status: Optional[str] = None


class AgentOrchestrator:
    """Agent 编排器 - 串起全流程"""

    def __init__(
        self,
        skill_registry: Optional[SkillRegistry] = None,
        tool_registry: Optional[ToolRegistry] = None,
        planner_config: Optional[PlannerConfig] = None,
    ):
        self.skill_registry = skill_registry or get_default_skill_registry()
        self.tool_registry = tool_registry or get_default_registry()
        self.planner = create_planner(planner_config or PlannerConfig())
        self.executor = Executor(self.tool_registry)

    async def _parse_skills(self, request: AgentRequest) -> List[Any]:
        matched_skills = []

        if request.skills:
            for skill_name in request.skills:
                skill = self.skill_registry.get(skill_name)
                if skill:
                    matched_skills.append(skill)
        else:
            matched = self.skill_registry.match_skills(request.task)
            skill_map = {s.name: s for s in self.skill_registry._skills.values()}
            for m in matched:
                skill = skill_map.get(m.name)
                if skill:
                    matched_skills.append(skill)

        if not matched_skills:
            from .planner import RuleBasedPlanner

            rule_planner = RuleBasedPlanner()
            skill_matches = rule_planner._match_skill_by_keywords(request.task)
            skill_map = {s.name: s for s in self.skill_registry._skills.values()}
            for match in skill_matches:
                skill = skill_map.get(match.skill_name)
                if skill:
                    matched_skills.append(skill)

        if not matched_skills:
            matched = self.skill_registry.match_skills(request.task)
            if matched:
                skill_map = {s.name: s for s in self.skill_registry._skills.values()}
                for m in matched[:3]:
                    skill = skill_map.get(m.name)
                    if skill:
                        matched_skills.append(skill)

        return matched_skills

    def _build_context(self, request: AgentRequest) -> Dict[str, Any]:
        context = dict(request.context)

        if "ssh_manager" not in context:
            from app.services.ssh_manager import SSHManager

            context["ssh_manager"] = SSHManager()

        return context

    def _extract_findings_from_execution(
        self,
        execution_result: ExecutionResult,
        skill_name: str,
    ) -> List[Dict[str, Any]]:
        findings = []
        for step_exec in execution_result.step_executions:
            if step_exec.result and step_exec.result.output:
                output = step_exec.result.output
                if isinstance(output, dict):
                    findings.append(
                        {
                            "tool": step_exec.tool_name,
                            "data": output,
                        }
                    )
                elif isinstance(output, list):
                    for item in output:
                        if isinstance(item, dict):
                            findings.append(
                                {
                                    "tool": step_exec.tool_name,
                                    "data": item,
                                }
                            )
        return findings

    def _extract_recommendations_from_results(
        self,
        execution_result: ExecutionResult,
    ) -> List[str]:
        recommendations = []

        for step_exec in execution_result.step_executions:
            if step_exec.result and step_exec.result.metadata:
                risk_level = step_exec.result.metadata.get("risk_level", "")
                if risk_level == "high":
                    recommendations.append(
                        f"检测到 {step_exec.tool_name} 高风险问题，请立即处理"
                    )
                elif risk_level == "medium":
                    recommendations.append(
                        f"检测到 {step_exec.tool_name} 中风险问题，建议尽快处理"
                    )

        if not recommendations:
            recommendations.append("未发现高风险问题，建议保持当前安全配置")

        return recommendations

    def _determine_risk_level(
        self,
        execution_result: ExecutionResult,
    ) -> str:
        high_count = 0
        medium_count = 0

        for step_exec in execution_result.step_executions:
            if step_exec.result and step_exec.result.metadata:
                risk = step_exec.result.metadata.get("risk_level", "low")
                if risk == "high":
                    high_count += 1
                elif risk == "medium":
                    medium_count += 1

        if high_count > 0:
            return "high"
        elif medium_count > 0:
            return "medium"
        return "low"

    def _generate_final_summary(
        self,
        request: AgentRequest,
        execution_result: ExecutionResult,
        skill_results: List[StructuredResult],
    ) -> str:
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
                    for rec in sr.recommendations:
                        lines.append(f"  - {rec}")
                lines.append("")

        lines.append("\n## 结构化输出\n")
        structured = execution_result.structured_output
        lines.append(f"- 总步骤: {structured.get('summary', {}).get('total_steps', 0)}")
        lines.append(
            f"- 成功: {structured.get('summary', {}).get('successful_steps', 0)}"
        )
        lines.append(f"- 失败: {structured.get('summary', {}).get('failed_steps', 0)}")

        return "\n".join(lines)

    async def run(self, request: AgentRequest) -> FinalReport:
        report = FinalReport(
            request_id=request.id,
            task=request.task,
            status="running",
        )

        skills = await self._parse_skills(request)

        if not skills:
            report.status = "failed"
            report.raw_summary = "未找到匹配 skill，请尝试其他任务描述"
            return report

        skill_name = skills[0].name if skills else "unknown"
        report.skill_name = skill_name
        context = self._build_context(request)

        is_auto_remediation = skill_name == "auto_remediation"
        max_replan_attempts = (
            context.get("max_replan_attempts", 2) if is_auto_remediation else 0
        )
        replan_count = 0

        # ── 新流程: planner 输出 calls → build_steps 动态生成 PlanStep → executor 执行 ──
        try:
            # 尝试使用新版 plan_calls 接口
            planner_output: PlannerOutput = await self.planner.plan_calls(request, skills, context)
        except (AttributeError, TypeError):
            # 兼容旧版 planner（未实现 plan_calls 时回退到 plan）
            plan = await self.planner.plan(request, skills, context)
            plan_dict = self._serialize_plan(plan)
            report.plan = plan_dict
            return await self._execute_plan_and_build_report(
                plan, request, context, report,
                is_auto_remediation, max_replan_attempts, skills,
            )

        # 将 calls 展开为 Plan（通过 build_steps 动态生成步骤）
        plan = self._build_plan_from_calls(planner_output, request, skills, context)

        plan_dict = self._serialize_plan(plan)
        report.plan = plan_dict

        execution_result = await self.executor.execute_plan(
            plan, request, context, max_replan_attempts=max_replan_attempts
        )
        replan_count = getattr(execution_result, "replan_count", 0)

        # 组装报告（复用原有逻辑）
        return await self._assemble_report(
            request, execution_result, report, skills,
            is_auto_remediation, max_replan_attempts, replan_count,
        )

    def _build_plan_from_calls(
        self,
        output: PlannerOutput,
        request: AgentRequest,
        skills: List[Any],
        context: Dict[str, Any],
    ):
        """将 PlannerOutput 的 calls 通过 skill.build_steps() 展开为 Plan"""
        from .schemas import Plan, PlanStep

        skill_map = {s.name: s for s in skills}
        steps = []
        step_number = 1

        for call in output.calls:
            skill_obj = skill_map.get(call.skill)
            if not skill_obj:
                continue

            # 核心：动态构建执行步骤
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
    def _serialize_plan(plan) -> Optional[Dict[str, Any]]:
        """序列化 Plan 为字典"""
        if not hasattr(plan, "steps"):
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

    async def _execute_plan_and_build_report(
        self, plan, request, context, report,
        is_auto_remediation, max_replan_attempts, skills,
    ) -> FinalReport:
        """兼容路径：直接用已有 Plan 执行并组装报告"""
        execution_result = await self.executor.execute_plan(
            plan, request, context, max_replan_attempts=max_replan_attempts
        )
        replan_count = getattr(execution_result, "replan_count", 0)
        return await self._assemble_report(
            request, execution_result, report, skills,
            is_auto_remediation, max_replan_attempts, replan_count,
        )

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
        """组装最终报告（execution_result 已由调用方传入，无需重复执行）"""

        skill_results = []
        for skill in skills:
            skill_steps = [
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
                findings=self._extract_findings_from_execution(
                    execution_result, skill.name
                ),
                recommendations=self._extract_recommendations_from_results(
                    execution_result
                ),
                risk_level=self._determine_risk_level(execution_result),
                metadata={"skill": skill.name},
            )
            skill_results.append(structured_result)

        report.skill_results = skill_results
        report.structured_output = execution_result.structured_output
        report.total_duration_ms = execution_result.total_duration_ms
        report.replan_count = replan_count

        traces = []
        for step_exec in execution_result.step_executions:
            output_preview = None
            tool_result_summary = None
            verification_passed = None
            error_type = None

            if step_exec.result and step_exec.result.output:
                output_str = str(step_exec.result.output)
                output_preview = (
                    output_str[:200] + "..." if len(output_str) > 200 else output_str
                )
                tool_result_summary = (
                    output_str[:500] if len(output_str) > 500 else output_str
                )

            if step_exec.result and step_exec.result.metadata:
                verification_passed = step_exec.result.metadata.get(
                    "verification_passed"
                )
                error_type = step_exec.result.metadata.get("error_type")

            trace_entry = {
                "id": str(uuid.uuid4()),
                "plan_id": execution_result.plan_id,
                "step_id": step_exec.id,
                "step_number": step_exec.step_number,
                "tool_name": step_exec.tool_name,
                "tool_result_summary": tool_result_summary,
                "output_preview": output_preview,
                "status": step_exec.status.value
                if hasattr(step_exec.status, "value")
                else str(step_exec.status),
                "started_at": step_exec.started_at.isoformat()
                if step_exec.started_at
                else None,
                "completed_at": step_exec.completed_at.isoformat()
                if step_exec.completed_at
                else None,
                "duration_ms": step_exec.duration_ms,
                "success": step_exec.status == ExecutionStatus.COMPLETED,
                "error": step_exec.error,
                "verification_passed": verification_passed,
                "error_type": error_type,
            }
            traces.append(trace_entry)
        report.traces = traces

        all_recommendations = []
        all_risks = []
        all_commands = []
        all_evidence = []
        fixed_items = []
        unfixed_items = []
        blocked_items = []

        for sr in skill_results:
            all_recommendations.extend(sr.recommendations)
            if sr.risk_level == "high":
                all_risks.append(f"高风险: {sr.skill_name}")
            elif sr.risk_level == "medium":
                all_risks.append(f"中风险: {sr.skill_name}")
            for finding in sr.findings:
                all_evidence.append(finding)

        # 从 context 中获取 env_info（在 run() 方法中已构建）
        env_info = report.environment  # 可能为 None，后续检查
        if is_auto_remediation:
            exec_context = self._build_context(request)
            categorized_findings = exec_context.get("categorized_findings", {})
            findings = exec_context.get("all_findings", [])

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

                if any(
                    f"patch_{cat}" in successful_tools
                    for cat in ["pam", "ssh", "fw", "user"]
                ):
                    fixed_items.append(f"[{severity}] {title}")
                elif any(
                    f"patch_{cat}" in failed_tools
                    for cat in ["pam", "ssh", "fw", "user"]
                ):
                    failed_step = next(
                        (
                            s
                            for s in execution_result.step_executions
                            if s.tool_name.startswith("patch_")
                            and s.status == ExecutionStatus.FAILED
                        ),
                        None,
                    )
                    if (
                        failed_step
                        and failed_step.result
                        and failed_step.result.metadata.get("error_type")
                        == "permission_denied"
                    ):
                        blocked_items.append(f"[{severity}] {title} (权限不足)")
                    else:
                        unfixed_items.append(f"[{severity}] {title}")

            env_info_local = exec_context.get("env_info")
            if env_info_local:
                report.environment = {
                    "os_family": env_info_local.os_family,
                    "distribution": env_info_local.distribution,
                    "version": env_info_local.version,
                    "package_manager": env_info_local.package_manager,
                    "init_system": env_info_local.init_system,
                    "sudo_available": env_info_local.sudo_available,
                    "current_user": env_info_local.current_user,
                }

        report.fixed_items = fixed_items
        report.unfixed_items = unfixed_items
        report.blocked_items = blocked_items

        report.final = {
            "summary": self.executor.generate_summary(execution_result, {}),
            "evidence": all_evidence,
            "risks": all_risks,
            "recommendations": all_recommendations[:10],
            "commands": all_commands,
            "next_actions": [
                "持续监控系统状态",
                "定期执行安全审计",
            ],
            "fixed_items": fixed_items,
            "unfixed_items": unfixed_items,
            "blocked_items": blocked_items,
        }

        report.raw_summary = self._generate_final_summary(
            request, execution_result, skill_results
        )

        failed_step_count = sum(
            1
            for s in execution_result.step_executions
            if s.status == ExecutionStatus.FAILED
        )
        total_step_count = len(execution_result.step_executions)

        report.structured_output = {
            "execution_id": execution_result.id,
            "plan_id": execution_result.plan_id,
            "request_id": request.id,
            "status": execution_result.status.value,
            "summary": {
                "total_steps": total_step_count,
                "successful_steps": sum(
                    1
                    for s in execution_result.step_executions
                    if s.status == ExecutionStatus.COMPLETED
                ),
                "failed_steps": failed_step_count,
                "replanned_steps": replan_count,
                "total_duration_ms": execution_result.total_duration_ms,
            },
            "environment": report.environment,
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
                    if s.result and s.result.metadata
                    else None,
                    "verification_passed": s.result.metadata.get("verification_passed")
                    if s.result and s.result.metadata
                    else None,
                    "replan_count": 0,
                }
                for s in execution_result.step_executions
            ],
        }

        if execution_result.status == ExecutionStatus.COMPLETED:
            if failed_step_count > 0 and total_step_count > 0:
                if failed_step_count == total_step_count:
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

        # 检查权限阻塞（使用 report.environment 中已有的 env_info）
        local_env = report.environment
        if (
            is_auto_remediation
            and local_env
            and not local_env.get("sudo_available", True)
            and local_env.get("current_user") != "root"
        ):
            report.status = "blocked_by_permission"
            report.final_status = "blocked_by_permission"

        return report


async def run_agent_task(
    task: str,
    context: Optional[Dict[str, Any]] = None,
    skills: Optional[List[str]] = None,
    max_steps: int = 10,
) -> FinalReport:
    """便捷函数：运行 Agent 任务"""
    request = AgentRequest(
        task=task,
        context=context or {},
        skills=skills or [],
        max_steps=max_steps,
    )

    orchestrator = AgentOrchestrator()
    return await orchestrator.run(request)
