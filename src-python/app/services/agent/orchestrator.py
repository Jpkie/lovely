"""Agent Orchestrator - 串起全流程"""

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
from .planner import BasePlanner, PlannerConfig, create_planner
from .executor import Executor, ExecutionResult, ExecutionStatus
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

        plan = await self.planner.plan(request, skills, context)

        plan_dict = None
        if hasattr(plan, "steps"):
            plan_dict = {
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
        report.plan = plan_dict

        execution_result = await self.executor.execute_plan(plan, request, context)

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

        traces = []
        for step_exec in execution_result.step_executions:
            output_preview = None
            tool_result_summary = None
            if step_exec.result and step_exec.result.output:
                output_str = str(step_exec.result.output)
                output_preview = (
                    output_str[:200] + "..." if len(output_str) > 200 else output_str
                )
                tool_result_summary = (
                    output_str[:500] if len(output_str) > 500 else output_str
                )

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
            }
            traces.append(trace_entry)
        report.traces = traces

        all_recommendations = []
        all_risks = []
        all_commands = []
        all_evidence = []
        for sr in skill_results:
            all_recommendations.extend(sr.recommendations)
            if sr.risk_level == "high":
                all_risks.append(f"高风险: {sr.skill_name}")
            elif sr.risk_level == "medium":
                all_risks.append(f"中风险: {sr.skill_name}")
            for finding in sr.findings:
                all_evidence.append(finding)

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
        }

        report.raw_summary = self._generate_final_summary(
            request, execution_result, skill_results
        )

        report.structured_output = {
            "execution_id": execution_result.id,
            "plan_id": execution_result.plan_id,
            "request_id": request.id,
            "status": execution_result.status.value,
            "summary": {
                "total_steps": len(execution_result.step_executions),
                "successful_steps": sum(
                    1
                    for s in execution_result.step_executions
                    if s.status == ExecutionStatus.COMPLETED
                ),
                "failed_steps": sum(
                    1
                    for s in execution_result.step_executions
                    if s.status == ExecutionStatus.FAILED
                ),
                "total_duration_ms": execution_result.total_duration_ms,
            },
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
                    "tool_name": s.tool_name,
                    "status": s.status.value,
                    "duration_ms": s.duration_ms,
                    "error": s.error,
                }
                for s in execution_result.step_executions
            ],
        }

        if execution_result.status == ExecutionStatus.COMPLETED:
            report.status = "completed"
        elif execution_result.status == ExecutionStatus.FAILED:
            report.status = "failed"
        else:
            report.status = execution_result.status.value

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
