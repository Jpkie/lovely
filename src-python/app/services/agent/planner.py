"""Agent Planner - 规则计划器和 LLM 计划器预留"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
import uuid

from .schemas import AgentRequest, Plan, PlanStep


class PlanStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    PLANNED = "planned"
    FAILED = "failed"


class SkillMatch(BaseModel):
    """Skill 匹配结果"""

    skill_name: str
    confidence: float = 1.0
    parameters: Dict[str, Any] = Field(default_factory=dict)


class PlannerConfig(BaseModel):
    """Planner 配置"""

    max_skills_per_task: int = 3
    enable_llm_planner: bool = False
    llm_model: Optional[str] = None


class BasePlanner(ABC):
    """Planner 基类"""

    @abstractmethod
    async def plan(
        self,
        request: AgentRequest,
        available_skills: List[Any],
        context: Dict[str, Any],
    ) -> Plan:
        """生成执行计划"""
        pass


class RuleBasedPlanner(BasePlanner):
    """基于规则的计划器"""

    KEYWORD_MAPPING: Dict[str, List[str]] = {
        "host_triage": [
            "triage",
            "快速评估",
            "主机状态",
            "安全评估",
            "主机安全",
            "系统状态",
            "主机检查",
            "快速扫描",
        ],
        "log_investigation": [
            "日志",
            "log",
            "日志分析",
            "日志调查",
            "安全日志",
            "auth.log",
            "syslog",
            "journal",
        ],
        "process_hunt": [
            "进程",
            "process",
            "进程分析",
            "进程调查",
            "可疑进程",
            "进程检查",
            "进程监控",
        ],
        "port_hunt": [
            "端口",
            "port",
            "端口扫描",
            "开放端口",
            "端口检查",
            "网络端口",
            "端口调查",
        ],
        "ssh_audit": [
            "ssh",
            "sshd",
            "ssh审计",
            "ssh安全",
            "ssh配置",
            "认证",
            "authorized_keys",
        ],
        "fix_advisor": [
            "修复",
            "fix",
            "建议",
            "修复建议",
            "整改",
            "remediation",
            "修复步骤",
            "如何修复",
        ],
    }

    def __init__(self, config: Optional[PlannerConfig] = None):
        self.config = config or PlannerConfig()

    def _match_skill_by_keywords(self, task: str) -> List[SkillMatch]:
        task_lower = task.lower()
        matches = []

        for skill_name, keywords in self.KEYWORD_MAPPING.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in task_lower:
                    score += 1
            if score > 0:
                confidence = min(score / len(keywords), 1.0)
                matches.append(SkillMatch(skill_name=skill_name, confidence=confidence))

        matches.sort(key=lambda x: x.confidence, reverse=True)
        return matches[: self.config.max_skills_per_task]

    async def plan(
        self,
        request: AgentRequest,
        available_skills: List[Any],
        context: Dict[str, Any],
    ) -> Plan:
        skill_map = {s.name: s for s in available_skills}

        if request.skills:
            explicit_skills = []
            for skill_name in request.skills:
                skill = skill_map.get(skill_name)
                if skill:
                    explicit_skills.append(
                        SkillMatch(skill_name=skill.name, confidence=1.0)
                    )

            if explicit_skills:
                skill_matches = explicit_skills
            elif available_skills:
                skill_matches = [
                    SkillMatch(skill_name=available_skills[0].name, confidence=0.5)
                ]
            else:
                skill_matches = self._match_skill_by_keywords(request.task)
        else:
            skill_matches = self._match_skill_by_keywords(request.task)

            if not skill_matches and available_skills:
                skill_matches = [
                    SkillMatch(skill_name=available_skills[0].name, confidence=0.5)
                ]

        steps = []
        step_number = 1

        for match in skill_matches:
            skill = skill_map.get(match.skill_name)
            if not skill:
                continue

            for skill_step in skill.steps:
                steps.append(
                    PlanStep(
                        id=skill_step.id,
                        step_number=step_number,
                        description=f"[{skill.name}] {skill_step.name}: {skill_step.description}",
                        skill_id=skill.name,
                        tool_name=skill_step.tool_name,
                        parameters=skill_step.parameters,
                        status="pending",
                    )
                )
                step_number += 1

        return Plan(
            id=str(uuid.uuid4()),
            request_id=request.id,
            steps=steps,
            status="planned",
        )


class LLMPlanner(BasePlanner):
    """LLM 计划器（预留实现）"""

    def __init__(self, config: Optional[PlannerConfig] = None):
        self.config = config or PlannerConfig()
        self._llm_adapter = None

    def set_llm_adapter(self, adapter) -> None:
        """设置 LLM 适配器"""
        self._llm_adapter = adapter

    async def plan(
        self,
        request: AgentRequest,
        available_skills: List[Any],
        context: Dict[str, Any],
    ) -> Plan:
        if not self._llm_adapter:
            rule_planner = RuleBasedPlanner(self.config)
            return await rule_planner.plan(request, available_skills, context)

        skill_descriptions = "\n".join(
            [f"- {s.name}: {s.description}" for s in available_skills]
        )

        prompt = f"""任务: {request.task}

可用 Skills:
{skill_descriptions}

请选择一个或多个最合适的 Skill 来完成这个任务，并生成执行计划。
以 JSON 格式返回计划，格式如下:
{{
  "skills": ["skill_name1", "skill_name2"],
  "reasoning": "选择理由"
}}

只返回 JSON，不要有其他内容。"""

        from .schemas import Message, ModelRole

        messages = [Message(role=ModelRole.USER, content=prompt)]

        try:
            response = await self._llm_adapter.chat(messages)
            import json

            plan_data = json.loads(response.content)

            skill_names = plan_data.get("skills", [])

            skill_map = {s.name: s for s in available_skills}
            steps = []
            step_number = 1

            for skill_name in skill_names:
                skill = skill_map.get(skill_name)
                if not skill:
                    continue

                for skill_step in skill.steps:
                    steps.append(
                        PlanStep(
                            id=skill_step.id,
                            step_number=step_number,
                            description=f"[{skill.name}] {skill_step.name}",
                            skill_id=skill.name,
                            tool_name=skill_step.tool_name,
                            parameters=skill_step.parameters,
                            status="pending",
                        )
                    )
                    step_number += 1

            return Plan(
                id=str(uuid.uuid4()),
                request_id=request.id,
                steps=steps,
                status="planned",
            )
        except Exception:
            rule_planner = RuleBasedPlanner(self.config)
            return await rule_planner.plan(request, available_skills, context)


def create_planner(config: Optional[PlannerConfig] = None) -> BasePlanner:
    """创建计划器"""
    cfg = config or PlannerConfig()
    if cfg.enable_llm_planner:
        return LLMPlanner(cfg)
    return RuleBasedPlanner(cfg)
