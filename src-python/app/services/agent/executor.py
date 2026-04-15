"""Agent Executor - 逐步执行并记录 Trace"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid

from .schemas import AgentRequest, ExecutionTrace, Plan, PlanStep, ToolResult
from .tool_registry import AgentToolResult, ToolRegistry, ToolStatus


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepExecution(BaseModel):
    """步骤执行记录"""

    step_id: str
    step_number: int
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: ExecutionStatus = ExecutionStatus.PENDING
    result: Optional[AgentToolResult] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: int = 0
    error: Optional[str] = None


class ExecutionResult(BaseModel):
    """执行结果"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: str
    request_id: str
    step_executions: List[StepExecution] = Field(default_factory=list)
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_duration_ms: int = 0
    final_summary: Optional[str] = None
    structured_output: Dict[str, Any] = Field(default_factory=dict)


class Executor:
    """执行器 - 逐步执行计划步骤并记录 trace"""

    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry

    async def execute_step(
        self,
        step: PlanStep,
        context: Dict[str, Any],
    ) -> StepExecution:
        execution = StepExecution(
            step_id=step.id,
            step_number=step.step_number,
            tool_name=step.tool_name,
            parameters=step.parameters,
            status=ExecutionStatus.RUNNING,
            started_at=datetime.utcnow(),
        )

        try:
            result = await self.tool_registry.execute_tool(
                name=step.tool_name,
                parameters=step.parameters,
                context=context,
            )

            execution.result = result
            if result.status == ToolStatus.SUCCESS:
                execution.status = ExecutionStatus.COMPLETED
            else:
                execution.status = ExecutionStatus.FAILED
                execution.error = result.error

        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error = str(e)

        execution.completed_at = datetime.utcnow()
        if execution.started_at:
            execution.duration_ms = int(
                (execution.completed_at - execution.started_at).total_seconds() * 1000
            )

        return execution

    def _build_execution_trace(self, execution: StepExecution) -> ExecutionTrace:
        tool_results = []
        if execution.result:
            tool_results.append(
                ToolResult(
                    id=str(uuid.uuid4()),
                    tool_name=execution.tool_name,
                    parameters=execution.parameters,
                    output=execution.result.output,
                    error=execution.result.error,
                    exit_code=0 if execution.result.status == ToolStatus.SUCCESS else 1,
                    duration_ms=execution.duration_ms,
                    success=execution.result.status == ToolStatus.SUCCESS,
                )
            )

        return ExecutionTrace(
            id=str(uuid.uuid4()),
            plan_id="",
            step_id=execution.step_id,
            step_number=execution.step_number,
            tool_results=tool_results,
            status="completed"
            if execution.status == ExecutionStatus.COMPLETED
            else "failed",
            started_at=execution.started_at or datetime.utcnow(),
            completed_at=execution.completed_at,
        )

    async def execute_plan(
        self,
        plan: Plan,
        request: AgentRequest,
        context: Dict[str, Any],
    ) -> ExecutionResult:
        result = ExecutionResult(
            plan_id=plan.id,
            request_id=request.id,
            status=ExecutionStatus.RUNNING,
        )

        for step in plan.steps:
            step_exec = await self.execute_step(step, context)
            result.step_executions.append(step_exec)

            if step_exec.status == ExecutionStatus.FAILED:
                if step_exec.error and "SSH not connected" in step_exec.error:
                    result.status = ExecutionStatus.FAILED
                    break

        all_completed = all(
            s.status == ExecutionStatus.COMPLETED for s in result.step_executions
        )
        any_failed = any(
            s.status == ExecutionStatus.FAILED for s in result.step_executions
        )

        if all_completed:
            result.status = ExecutionStatus.COMPLETED
        elif any_failed:
            result.status = ExecutionStatus.FAILED

        result.completed_at = datetime.utcnow()
        result.total_duration_ms = sum(s.duration_ms for s in result.step_executions)

        return result

    def generate_summary(
        self,
        execution_result: ExecutionResult,
        skill_definitions: Dict[str, Any],
    ) -> str:
        lines = ["# 执行结果摘要\n"]

        lines.append(f"**状态**: {execution_result.status.value}")
        lines.append(f"**总步骤**: {len(execution_result.step_executions)}")
        lines.append(f"**总耗时**: {execution_result.total_duration_ms}ms\n")

        successful = [
            s
            for s in execution_result.step_executions
            if s.status == ExecutionStatus.COMPLETED
        ]
        failed = [
            s
            for s in execution_result.step_executions
            if s.status == ExecutionStatus.FAILED
        ]

        lines.append(f"**成功**: {len(successful)}, **失败**: {len(failed)}\n")

        if failed:
            lines.append("## 失败步骤\n")
            for step_exec in failed:
                lines.append(f"- {step_exec.tool_name}: {step_exec.error}")

        lines.append("\n## 执行详情\n")
        for step_exec in execution_result.step_executions:
            status_icon = "✓" if step_exec.status == ExecutionStatus.COMPLETED else "✗"
            lines.append(
                f"{status_icon} [{step_exec.step_number}] {step_exec.tool_name}"
            )
            if step_exec.result and step_exec.result.output:
                output_str = str(step_exec.result.output)
                if len(output_str) > 200:
                    output_str = output_str[:200] + "..."
                lines.append(f"   输出: {output_str}")

        return "\n".join(lines)

    def generate_structured_output(
        self,
        execution_result: ExecutionResult,
    ) -> Dict[str, Any]:
        structured = {
            "execution_id": execution_result.id,
            "plan_id": execution_result.plan_id,
            "request_id": execution_result.request_id,
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
            "steps": [],
        }

        for step_exec in execution_result.step_executions:
            step_data = {
                "step_id": step_exec.step_id,
                "step_number": step_exec.step_number,
                "tool_name": step_exec.tool_name,
                "status": step_exec.status.value,
                "duration_ms": step_exec.duration_ms,
                "output": None,
                "error": step_exec.error,
            }

            if step_exec.result:
                step_data["output"] = step_exec.result.output
                step_data["metadata"] = step_exec.result.metadata

            structured["steps"].append(step_data)

        return structured
