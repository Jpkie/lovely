"""Agent Planner - 规则计划器和 LLM 计划器

新版架构: 用户任务 -> planner 输出 SkillCall(skill, args, confidence) -> skill.build_steps(args, ctx) -> executor
"""

from abc import ABC, abstractmethod
from enum import Enum
import json
import re
import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .schemas import AgentRequest, Plan, PlanStep, PlannerOutput, SkillCall


class PlanStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    PLANNED = "planned"
    FAILED = "failed"


class SkillMatch(BaseModel):
    """Skill 匹配结果（兼容旧接口）"""

    skill_name: str
    confidence: float = 1.0
    parameters: Dict[str, Any] = Field(default_factory=dict)


class PlannerConfig(BaseModel):
    """Planner 配置"""

    max_skills_per_task: int = 3
    enable_llm_planner: bool = False
    llm_model: Optional[str] = None


class BasePlanner(ABC):
    """Planner 基类

    新版 plan() 返回包含 calls 字段的 PlannerOutput，
    由 orchestrator 调用 skill.build_steps() 将 calls 展开为 PlanStep。
    """

    @abstractmethod
    async def plan(
        self,
        request: AgentRequest,
        available_skills: List[Any],
        context: Dict[str, Any],
    ) -> Plan:
        """生成执行计划（返回 Plan，内部通过 _build_plan_from_output 构建）"""
        pass

    async def plan_calls(
        self,
        request: AgentRequest,
        available_skills: List[Any],
        context: Dict[str, Any],
    ) -> PlannerOutput:
        """返回结构化的 Skill 调用列表（新版核心接口）

        Returns:
            PlannerOutput(calls=[SkillCall(skill, args, confidence)], reasoning=...)
        """
        # 默认回退到 plan() 并反推 calls（兼容未覆写的子类）
        plan = await self.plan(request, available_skills, context)
        # 从已有 Plan 反推最简 calls（仅用于兼容）
        calls = []
        seen_skills = set()
        for step in plan.steps:
            if step.skill_id and step.skill_id not in seen_skills:
                calls.append(SkillCall(skill=step.skill_name or step.skill_id, args={}, confidence=0.8))
                seen_skills.add(step.skill_id)
        return PlannerOutput(calls=calls, reasoning="从旧版 plan() 反推")


# ── 规则提取：从自然语言中提取常见参数模式 ──

_PARAM_PATTERNS = {
    "log_path": [
        re.compile(r"(?:日志|log)[文件路径\s]*[:：]?\s*([\w/.\-]+)", re.I),
        re.compile(r"([\w/.\-]+(?:auth|syslog|message|kernel|btmp)\.log)", re.I),
    ],
    "process_name": [
        re.compile(r"(?:进程名?|process)[名称\s]*[:：]?\s*(\w+)", re.I),
        re.compile(r"查找[进程\s]*(\w+)\s*(?:进程)?", re.I),
    ],
    "keywords": [
        re.compile(r"(?:搜索|查找|关键词|keyword)[:\s]+(.+?)(?:[,;。]|$)", re.I),
        re.compile(r"包含[关键词\s]*[:：]?\s*(.+?)(?:[,;。]|$)", re.I),
    ],
    "ssh_config_path": [
        re.compile(r"(?:ssh.*配置|sshd_config)[路径\s]*[:：]?\s*([\w/.\-]+)", re.I),
        re.compile(r"([\w/.\-]*sshd[_\-]?config[\w/.\-]*)", re.I),
    ],
}


def extract_params_by_rules(task: str, skill_name: str) -> Dict[str, Any]:
    """基于正则从自然语言中提取参数"""
    params: Dict[str, Any] = {}

    for param_name, patterns in _PARAM_PATTERNS.items():
        for pattern in patterns:
            match = pattern.search(task)
            if match:
                value = match.group(1).strip()
                if param_name == "keywords":
                    params[param_name] = [k.strip() for k in value.split(",") if k.strip()]
                else:
                    params[param_name] = value
                break

    # 日志调查特殊处理：如果用户提到具体日志类型
    if skill_name == "log_investigation":
        if "auth" in task.lower():
            params.setdefault("log_path", "/var/log/auth.log")
        elif "syslog" in task.lower() or "系统日志" in task:
            params.setdefault("log_path", "/var/log/syslog")

    # 进程特殊处理
    if skill_name == "process_hunt":
        top_match = re.search(r"前(\d+)个?", task)
        if top_match:
            params["top_n"] = int(top_match.group(1))
        if "内存" in task and "cpu" not in task.lower():
            params["sort_by"] = "memory"

    return params


class RuleBasedPlanner(BasePlanner):
    """基于规则的计划器（增强版：支持基础参数提取）"""

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

    async def plan(self, request: AgentRequest, available_skills: List[Any], context: Dict[str, Any]) -> Plan:
        """生成 Plan（兼容旧接口）"""
        output = await self.plan_calls(request, available_skills, context)
        return self._build_plan_from_output(output, request, available_skills, context)

    async def plan_calls(self, request: AgentRequest, available_skills: List[Any], context: Dict[str, Any]) -> PlannerOutput:
        """返回带参数的 Skill 调用列表（新版核心）"""
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
                skill_matches = [SkillMatch(skill_name=available_skills[0].name, confidence=0.5)]
            else:
                skill_matches = self._match_skill_by_keywords(request.task)
        else:
            skill_matches = self._match_skill_by_keywords(request.task)
            if not skill_matches and available_skills:
                skill_matches = [SkillMatch(skill_name=available_skills[0].name, confidence=0.5)]

        # ── 构建新的 calls 列表（含参数提取）──
        calls: List[SkillCall] = []
        reasoning_parts = []

        for match in skill_matches:
            skill_obj = skill_map.get(match.skill_name)
            if not skill_obj:
                continue

            # 从用户输入的自然语言中提取参数
            extracted_args = extract_params_by_rules(request.task, match.skill_name)

            call = SkillCall(
                skill=match.skill_name,
                args=extracted_args,
                confidence=match.confidence,
            )
            calls.append(call)

            if extracted_args:
                reasoning_parts.append(f"[{match.skill_name}] 提取参数: {list(extracted_args.keys())}")
            else:
                reasoning_parts.append(f"[{match.skill_name}] 使用默认参数")

        return PlannerOutput(
            calls=calls,
            reasoning=f"规则匹配完成: {'; '.join(reasoning_parts)}",
        )

    def _build_plan_from_output(
        self,
        output: PlannerOutput,
        request: AgentRequest,
        available_skills: List[Any],
        context: Dict[str, Any],
    ) -> Plan:
        """将 PlannerOutput 的 calls 展开为 Plan（含 build_steps 动态构建）"""
        skill_map = {s.name: s for s in available_skills}
        steps = []
        step_number = 1

        for call in output.calls:
            skill = skill_map.get(call.skill)
            if not skill:
                continue

            # 核心：调用 skill.build_steps(args, context) 动态生成步骤
            dynamic_steps = skill.build_steps(call.args, context)

            for skill_step in dynamic_steps:
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
    """LLM 计划器（新版：输出 calls 格式）"""

    def __init__(self, config: Optional[PlannerConfig] = None):
        self.config = config or PlannerConfig()
        self._llm_adapter = None

    def set_llm_adapter(self, adapter) -> None:
        """设置 LLM 适配器"""
        self._llm_adapter = adapter

    async def plan(self, request: AgentRequest, available_skills: List[Any], context: Dict[str, Any]) -> Plan:
        """生成 Plan（兼容旧接口）"""
        output = await self.plan_calls(request, available_skills, context)
        rule_planner = RuleBasedPlanner(self.config)
        return rule_planner._build_plan_from_output(output, request, available_skills, context)

    async def plan_calls(self, request: AgentRequest, available_skills: List[Any], context: Dict[str, Any]) -> PlannerOutput:
        """返回 LLM 生成的 Skill 调用列表（新版输出格式）"""
        if not self._llm_adapter:
            # 无 LLM 适配器时回退到规则规划器
            rule_planner = RuleBasedPlanner(self.config)
            return await rule_planner.plan_calls(request, available_skills, context)

        # 构造 skill 描述（含参数信息，让 LLM 知道可填什么参数）
        skill_descriptions = []
        for s in available_skills:
            param_info = ""
            if s.parameters:
                param_descs = [f"  - {p.name} ({p.type}): {p.description}" for p in s.parameters]
                param_info = f"\n  参数:\n" + "\n".join(param_descs)
            skill_descriptions.append(f"- **{s.name}**: {s.description}{param_info}")

        skills_text = "\n".join(skill_descriptions)

        prompt = f"""任务: {request.task}

可用 Skills:
{skills_text}

请选择一个或多个最合适的 Skill 来完成这个任务，并从任务描述中提取每个 Skill 所需的参数。
以 JSON 格式返回，格式如下:
{{
  "calls": [
    {{
      "skill": "skill_name",
      "args": {{ "param1": "value1" }},
      "confidence": 0.95
    }}
  ],
  "reasoning": "为什么选择这些 skill 和参数"
}}

注意：
- args 中只填写你能从任务描述中明确推断出的参数，不确定的不要填
- confidence 是 0~1 之间的浮点数
- 只返回 JSON，不要有其他内容。"""

        from .schemas import Message, ModelRole

        messages = [Message(role=ModelRole.USER, content=prompt)]

        try:
            response = await self._llm_adapter.chat(messages)
            raw_data = json.loads(response.content)

            # 兼容旧格式 {"skills": [...]} → 自动转换为新格式
            if "skills" in raw_data and "calls" not in raw_data:
                raw_data["calls"] = [
                    SkillCall(skill=name, args={}, confidence=0.8).model_dump()
                    for name in raw_data.get("skills", [])
                ]

            output = PlannerOutput.model_validate(raw_data)

            # 验证并过滤无效的 calls
            valid_skill_names = {s.name for s in available_skills}
            output.calls = [
                c for c in output.calls if c.skill in valid_skill_names
            ]

            if not output.calls:
                output.reasoning += " (LLM 返回的 skill 无效，已清空)"

            return output

        except Exception:
            # LLM 解析失败时回退到规则规划器
            rule_planner = RuleBasedPlanner(self.config)
            return await rule_planner.plan_calls(request, available_skills, context)


def create_planner(config: Optional[PlannerConfig] = None) -> BasePlanner:
    """创建计划器"""
    cfg = config or PlannerConfig()
    if cfg.enable_llm_planner:
        return LLMPlanner(cfg)
    return RuleBasedPlanner(cfg)
