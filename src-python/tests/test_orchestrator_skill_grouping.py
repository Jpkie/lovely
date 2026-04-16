"""Orchestrator 多 skill 归组测试

验证:
  - 按 skill_id 分组 step_executions
  - 每个 StructuredResult 只包含该 skill 的步骤数据
  - 不同 skill 的 findings / recommendations / risk_level 不串数据
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, AsyncMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.agent.orchestrator import AgentOrchestrator, StructuredResult
from app.services.agent.executor import StepExecution, ExecutionStatus, ExecutionResult
from app.services.agent.tool_registry import AgentToolResult, ToolStatus


def _make_step_execution(
    tool_name: str,
    skill_id: str,
    risk_level: str = "low",
    output=None,
) -> StepExecution:
    """创建测试用 StepExecution"""
    result = None
    if output is not None or risk_level != "low":
        result = AgentToolResult(
            tool_name=tool_name,
            status=ToolStatus.SUCCESS,
            output=output or {"data": "test"},
            metadata={"risk_level": risk_level} if risk_level != "low" else {},
        )
    return StepExecution(
        step_id=f"step_{tool_name}_{skill_id}",
        step_number=1,
        tool_name=tool_name,
        skill_id=skill_id,
        status=ExecutionStatus.COMPLETED,
        result=result,
    )


class TestOrchestratorSkillGrouping:
    """多 Skill 任务下 skill_results 不串数据"""

    def test_group_steps_by_skill_basic(self):
        """_group_steps_by_skill 基本分组"""
        steps = [
            _make_step_execution("detect_log", "log_investigation"),
            _make_step_execution("read_system_log", "log_investigation"),
            _make_step_execution("detect_process", "process_hunt"),
            _make_step_execution("process_list", "process_hunt"),
        ]
        groups = AgentOrchestrator._group_steps_by_skill(steps)

        assert "log_investigation" in groups
        assert "process_hunt" in groups
        assert len(groups["log_investigation"]) == 2
        assert len(groups["process_hunt"]) == 2

    def test_group_steps_with_no_skill_id(self):
        """无 skill_id 的步骤归入 __unknown__"""
        steps = [
            _make_step_execution("detect_log", None),
        ]
        groups = AgentOrchestrator._group_steps_by_skill(steps)
        assert "__unknown__" in groups

    def test_findings_not_cross_contaminated(self):
        """不同 skill 的 findings 不串数据"""
        log_steps = [
            _make_step_execution("detect_log", "log_investigation",
                                 output={"log_issue": "auth failure"}),
            _make_step_execution("read_system_log", "log_investigation",
                                 output={"entries": 100}),
        ]
        proc_steps = [
            _make_step_execution("detect_process", "process_hunt",
                                 output={"proc_issue": "suspicious"}),
        ]

        log_findings = AgentOrchestrator._extract_findings_from_steps(log_steps)
        proc_findings = AgentOrchestrator._extract_findings_from_steps(proc_steps)

        # log_findings 应包含 detect_log 和 read_system_log
        log_tools = {f["tool"] for f in log_findings}
        assert "detect_log" in log_tools
        assert "read_system_log" in log_tools
        assert "detect_process" not in log_tools

        # proc_findings 应只包含 detect_process
        proc_tools = {f["tool"] for f in proc_findings}
        assert "detect_process" in proc_tools
        assert "detect_log" not in proc_tools

    def test_recommendations_per_skill(self):
        """不同 skill 的 recommendations 不串"""
        log_steps = [
            _make_step_execution("detect_log", "log_investigation", risk_level="high"),
        ]
        proc_steps = [
            _make_step_execution("detect_process", "process_hunt", risk_level="medium"),
        ]

        log_recs = AgentOrchestrator._extract_recommendations_from_steps(log_steps)
        proc_recs = AgentOrchestrator._extract_recommendations_from_steps(proc_steps)

        # log 应有高风险建议
        assert any("高风险" in r for r in log_recs)
        assert not any("中风险" in r for r in log_recs)

        # process 应有中风险建议
        assert any("中风险" in r for r in proc_recs)
        assert not any("高风险" in r for r in proc_recs)

    def test_risk_level_per_skill(self):
        """不同 skill 的 risk_level 独立计算"""
        log_steps = [
            _make_step_execution("detect_log", "log_investigation", risk_level="high"),
        ]
        proc_steps = [
            _make_step_execution("detect_process", "process_hunt", risk_level="low"),
        ]
        empty_steps = []

        assert AgentOrchestrator._determine_risk_level_from_steps(log_steps) == "high"
        assert AgentOrchestrator._determine_risk_level_from_steps(proc_steps) == "low"
        assert AgentOrchestrator._determine_risk_level_from_steps(empty_steps) == "low"

    def test_multi_skill_integration(self):
        """集成测试：两个 skill 的 StructuredResult 互不干扰"""
        steps = [
            _make_step_execution("detect_log", "log_investigation",
                                 risk_level="high", output={"issue": "brute force"}),
            _make_step_execution("read_system_log", "log_investigation",
                                 output={"count": 50}),
            _make_step_execution("detect_process", "process_hunt",
                                 risk_level="medium", output={"suspicious": True}),
            _make_step_execution("process_list", "process_hunt",
                                 output={"total": 120}),
        ]

        groups = AgentOrchestrator._group_steps_by_skill(steps)

        log_steps = groups.get("log_investigation", [])
        proc_steps = groups.get("process_hunt", [])

        # 各自的 findings
        log_findings = AgentOrchestrator._extract_findings_from_steps(log_steps)
        proc_findings = AgentOrchestrator._extract_findings_from_steps(proc_steps)

        assert len(log_findings) == 2  # detect_log + read_system_log
        assert len(proc_findings) == 2  # detect_process + process_list

        # 各自的风险等级
        assert AgentOrchestrator._determine_risk_level_from_steps(log_steps) == "high"
        assert AgentOrchestrator._determine_risk_level_from_steps(proc_steps) == "medium"
