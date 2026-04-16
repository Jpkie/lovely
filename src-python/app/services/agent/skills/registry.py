"""Skills 注册表

架构说明:
  - BaseSkill 是参数化 Skill 的抽象基类
  - 每个 Skill 通过 parameters 声明可接受的输入参数
  - Planner 从自然语言提取参数后，调用 skill.build_steps(args, context) 动态生成执行步骤
  - 向后兼容：旧版固定 steps 模式仍可通过覆写 steps 属性 + build_steps 返回 self.steps 实现
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid

from ..schemas import SkillParameter


# ────────────────── 数据模型 ──────────────────


class SkillStep(BaseModel):
    """Skill 执行步骤"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(description="步骤名称")
    description: str = Field(description="步骤描述")
    tool_name: str = Field(description="要调用的工具名")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="传给工具的参数")
    depends_on: List[str] = Field(default_factory=list, description="依赖的前置步骤 ID")


class SkillDefinition(BaseModel):
    """Skill 定义（对外暴露的只读元数据）

    由 BaseSkill.get_definition() 生成，供前端展示 / Planner 参考使用。
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(description="Skill 名称")
    description: str = Field(default="", description="Skill 描述")
    category: str = Field(default="general", description="分类标签")
    steps: List[SkillStep] = Field(
        default_factory=list,
        description="默认/示例执行步骤（build_steps 未调用时的静态快照）",
    )
    parameters: List[SkillParameter] = Field(
        default_factory=list,
        description="Skill 可接受的输入参数定义（Schema）",
    )
    required_context_keys: List[str] = Field(
        default_factory=list,
        description="执行所需的上下文 key 列表",
    )
    output_template: str = Field(default="", description="结果输出模板")


# ────────────────── 抽象基类 ──────────────────


class BaseSkill(ABC):
    """Skill 抽象基类 — 参数化动态构建模式

    子类必须实现:
      - name / description / category (基本元信息)
      - build_steps(args, context) (核心：根据参数生成执行步骤)

    子类可选覆写:
      - steps: 静态默认步骤（build_steps 默认实现可直接返回 self.steps）
      - parameters: 声明可接受的输入参数 Schema（供 Planner 参考）
      - required_context_keys / output_template

    调用链:
      用户任务 → Planner 输出 SkillCall(skill, args)
              → skill.build_steps(args, ctx) → [SkillStep, ...]
              → Executor 逐步执行 → 收集结果
    """

    # ── 必须实现的属性 ──

    @property
    @abstractmethod
    def name(self) -> str:
        """Skill 唯一标识符"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """自然语言描述（用于匹配和展示）"""
        ...

    @property
    @abstractmethod
    def category(self) -> str:
        """分类标签（triage / investigation / audit / remediation ...）"""
        ...

    # ── 核心：动态构建方法 ──

    @abstractmethod
    def build_steps(self, args: Dict[str, Any], context: Dict[str, Any]) -> List[SkillStep]:
        """根据 Planner 提取的参数动态构建执行步骤

        这是新版架构的核心入口。Planner 从自然语言任务中提取参数后，
        将 args 和上下文传入此方法，由 Skill 决定具体执行哪些步骤。

        Args:
            args: Planner 提取的参数字典。
                  例如 LogInvestigation 可能收到 {"log_path": "/var/log/auth.log", "keywords": ["failed"]}
            context: 执行上下文，通常包含 "ssh_manager" 等运行时对象。

        Returns:
            有序的 SkillStep 列表，每个 step 对应一次工具调用。
            Executor 将按顺序逐步执行这些步骤。
        """
        ...

    # ── 可选覆写的属性 ──

    @property
    def steps(self) -> List[SkillStep]:
        """静态默认步骤（向后兼容入口）

        对于不需要动态参数的简单 Skill，可以仅覆写此属性，
        并在 build_steps 中直接 return self.steps。
        """
        return []

    @property
    def parameters(self) -> List[SkillParameter]:
        """Skill 的输入参数 Schema 定义

        返回值用于：
          1. Planner 理解该 Skill 可以接受什么参数
          2. LLM Planner 在 prompt 中向模型展示可用参数
          3. 前端 UI 展示参数填写表单

        示例:
            return [
                SkillParameter(name="log_path", type="string",
                               description="日志文件路径", default="/var/log/auth.log"),
            ]
        """
        return []

    @property
    def required_context_keys(self) -> List[str]:
        """执行时 context 中必须存在的 key"""
        return []

    @property
    def output_template(self) -> str:
        """最终报告模板（支持 {变量} 占位符）"""
        return ""

    # ── 工具方法 ──

    def get_definition(self) -> SkillDefinition:
        """导出对外可见的 Skill 元数据"""
        return SkillDefinition(
            id=self.name,
            name=self.name,
            description=self.description,
            category=self.category,
            steps=self.steps,           # 静态快照
            parameters=self.parameters,   # 参数 Schema
            required_context_keys=self.required_context_keys,
            output_template=self.output_template,
        )


# ────────────────── 注册表 ──────────────────


class SkillRegistry:
    """Skill 注册中心

    用法:
        registry = SkillRegistry()
        registry.register(MySkill())
        skill = registry.get("my_skill")
        all_defs = registry.list_skills()
    """

    def __init__(self) -> None:
        self._skills: Dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        """注册一个 Skill 实例"""
        self._skills[skill.name] = skill

    def get(self, name: str) -> Optional[BaseSkill]:
        """按名称获取 Skill 实例"""
        return self._skills.get(name)

    def list_skills(self) -> List[SkillDefinition]:
        """列出所有已注册 Skill 的元数据"""
        return [skill.get_definition() for skill in self._skills.values()]

    def list_by_category(self, category: str) -> List[SkillDefinition]:
        """按分类筛选 Skill 元数据"""
        return [
            skill.get_definition()
            for skill in self._skills.values()
            if skill.category == category
        ]

    def has_skill(self, name: str) -> bool:
        """检查是否已注册某 Skill"""
        return name in self._skills

    def match_skills(self, query: str) -> List[SkillDefinition]:
        """模糊搜索匹配的 Skill（按 name / description / category）"""
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

    def iter_skills(self):
        """公开实例遍历方法 — 返回已注册 Skill 实例的迭代器

        用法:
            for skill_instance in registry.iter_skills():
                ...
        """
        return iter(self._skills.values())

    def get_all_skill_instances(self) -> List[BaseSkill]:
        """获取所有已注册 Skill 实例列表（只读快照）"""
        return list(self._skills.values())
