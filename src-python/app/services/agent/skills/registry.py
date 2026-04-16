"""Skills 注册表"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid

from ..schemas import SkillParameter


class SkillStep(BaseModel):
    """Skill 执行步骤"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)


class SkillDefinition(BaseModel):
    """Skill 定义（对外暴露的元数据）"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    category: str = "general"
    steps: List[SkillStep] = Field(default_factory=list)
    parameters: List[SkillParameter] = Field(default_factory=list)  # 新增：参数定义
    required_context_keys: List[str] = Field(default_factory=list)
    output_template: str = ""


class BaseSkill(ABC):
    """Skill 基类

    支持两种模式：
    1. 固定 steps 模式（旧兼容）：子类实现 steps 属性，build_steps 默认返回 self.steps
    2. 参数化动态构建模式（新）：子类实现 parameters 属性 + build_steps(args, context)
       根据从自然语言提取的参数动态生成执行步骤
    """

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    @abstractmethod
    def category(self) -> str:
        pass

    # ── 不再是抽象属性：子类可选择性覆写 ──

    @property
    def steps(self) -> List[SkillStep]:
        """固定步骤（默认空列表，子类可覆写以提供默认步骤）"""
        return []

    @property
    def parameters(self) -> List[SkillParameter]:
        """Skill 的输入参数定义（子类覆写以支持参数化）"""
        return []

    def build_steps(self, args: Dict[str, Any], context: Dict[str, Any]) -> List[SkillStep]:
        """根据参数动态构建执行步骤

        Args:
            args: 从 Planner 提取的参数字典
            context: 执行上下文（含 ssh_manager 等）

        Returns:
            动态生成的 SkillStep 列表
        """
        # 默认行为：返回固定 steps（向后兼容）
        return self.steps

    def get_definition(self) -> SkillDefinition:
        return SkillDefinition(
            id=self.name,
            name=self.name,
            description=self.description,
            category=self.category,
            steps=self.steps,
            parameters=self.parameters,  # 新增暴露参数定义
            required_context_keys=self.required_context_keys,
            output_template=self.output_template,
        )

    @property
    def required_context_keys(self) -> List[str]:
        return []

    @property
    def output_template(self) -> str:
        return ""


class SkillRegistry:
    """Skill 注册表"""

    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        self._skills[skill.name] = skill

    def get(self, name: str) -> Optional[BaseSkill]:
        return self._skills.get(name)

    def list_skills(self) -> List[SkillDefinition]:
        return [skill.get_definition() for skill in self._skills.values()]

    def list_by_category(self, category: str) -> List[SkillDefinition]:
        return [
            skill.get_definition()
            for skill in self._skills.values()
            if skill.category == category
        ]

    def has_skill(self, name: str) -> bool:
        return name in self._skills

    def match_skills(self, query: str) -> List[SkillDefinition]:
        query_lower = query.lower()
        matched = []
        for skill in self._skills.values():
            if (
                query_lower in skill.name.lower()
                or query_lower in skill.description.lower()
                or query_lower in skill.category.lower()
            ):
                matched.append(skill.get_definition())
        return matched