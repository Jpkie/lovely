"""Skills 注册表"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


class SkillStep(BaseModel):
    """Skill 执行步骤"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)


class SkillDefinition(BaseModel):
    """Skill 定义"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    category: str = "general"
    steps: List[SkillStep] = Field(default_factory=list)
    required_context_keys: List[str] = Field(default_factory=list)
    output_template: str = ""


class BaseSkill(ABC):
    """Skill 基类"""

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

    @property
    @abstractmethod
    def steps(self) -> List[SkillStep]:
        pass

    @property
    def required_context_keys(self) -> List[str]:
        return []

    @property
    def output_template(self) -> str:
        return ""

    def get_definition(self) -> SkillDefinition:
        return SkillDefinition(
            id=self.name,
            name=self.name,
            description=self.description,
            category=self.category,
            steps=self.steps,
            required_context_keys=self.required_context_keys,
            output_template=self.output_template,
        )


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
