"""Agent Tool 系统 - 注册表与结果定义"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Awaitable
from pydantic import BaseModel, Field
import uuid

from .schemas import SkillDefinition


class ToolStatus(str, Enum):
    """工具执行状态"""

    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


class AgentToolResult(BaseModel):
    """Agent Tool 执行结果 - 统一返回格式"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    status: ToolStatus = ToolStatus.SUCCESS
    output: Optional[Any] = None
    error: Optional[str] = None
    duration_ms: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BaseTool(ABC):
    """Tool 基类"""

    def __init__(self):
        self._definition: Optional[SkillDefinition] = None

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
    def parameters(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        pass

    def get_definition(self) -> SkillDefinition:
        if self._definition is None:
            self._definition = SkillDefinition(
                id=self.name,
                name=self.name,
                description=self.description,
                parameters=[],
                enabled=True,
            )
        return self._definition


ToolExecutor = Callable[[Dict[str, Any], Dict[str, Any]], Awaitable[AgentToolResult]]


class ToolRegistry:
    """Tool 注册表"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._executors: Dict[str, ToolExecutor] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def register_executor(self, name: str, executor: ToolExecutor) -> None:
        self._executors[name] = executor

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def get_executor(self, name: str) -> Optional[ToolExecutor]:
        return self._executors.get(name)

    def list_tools(self) -> List[SkillDefinition]:
        return [tool.get_definition() for tool in self._tools.values()]

    def list_tool_names(self) -> List[str]:
        return list(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        return name in self._tools or name in self._executors

    async def execute_tool(
        self, name: str, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        start_time = datetime.utcnow()

        if name in self._executors:
            try:
                result = await self._executors[name](parameters, context)
                duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                if isinstance(result, AgentToolResult):
                    result.duration_ms = duration
                    return result
                return AgentToolResult(
                    tool_name=name,
                    status=ToolStatus.SUCCESS,
                    output=result,
                    duration_ms=duration,
                )
            except Exception as e:
                duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                return AgentToolResult(
                    tool_name=name,
                    status=ToolStatus.ERROR,
                    error=str(e),
                    duration_ms=duration,
                )

        tool = self._tools.get(name)
        if tool is None:
            return AgentToolResult(
                tool_name=name,
                status=ToolStatus.ERROR,
                error=f"Tool not found: {name}",
            )

        try:
            return await tool.execute(parameters, context)
        except Exception as e:
            duration = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            return AgentToolResult(
                tool_name=name,
                status=ToolStatus.ERROR,
                error=str(e),
                duration_ms=duration,
            )

    def merge(self, other: "ToolRegistry") -> None:
        for name, tool in other._tools.items():
            self._tools[name] = tool
        for name, executor in other._executors.items():
            self._executors[name] = executor


async def load_mcp_tools(mcp_config: Dict[str, Any]) -> ToolRegistry:
    """加载 MCP tools

    Args:
        mcp_config: MCP 配置信息

    Returns:
        ToolRegistry: 包含 MCP tools 的注册表
    """
    registry = ToolRegistry()
    try:
        from .mcp import MCPAdapter

        adapter = MCPAdapter.from_config(mcp_config)
        if adapter.enabled and await adapter.initialize():
            tools = await adapter.list_tools()
            for tool in tools:
                from .schemas import SkillDefinition, SkillParameter, SkillType

                skill_def = SkillDefinition(
                    id=f"mcp_{tool.name}",
                    name=tool.name,
                    description=tool.description,
                    skill_type=SkillType.CUSTOM,
                    parameters=[
                        SkillParameter(
                            name=p.get("name", ""),
                            type=p.get("type", "string"),
                            description=p.get("description", ""),
                            required=p.get("required", False),
                        )
                        for p in tool.input_schema.get("properties", {}).values()
                    ],
                    enabled=tool.enabled,
                )
                registry.register(skill_def)
    except Exception:
        pass
    return registry


async def load_mcp_tools_if_enabled(settings: Any) -> ToolRegistry:
    """根据设置加载 MCP tools (如果启用)

    Args:
        settings: AppSettings 实例

    Returns:
        ToolRegistry: 合并后的注册表
    """
    registry = ToolRegistry()

    try:
        mcp_enabled = False
        if hasattr(settings, "mcp_enabled"):
            mcp_enabled = settings.mcp_enabled
        elif hasattr(settings, "agent") and settings.agent:
            mcp_enabled = getattr(settings.agent, "mcp_enabled", False)

        if not mcp_enabled:
            return registry

        mcp_config = getattr(settings, "mcp", None) or {}
        if not mcp_config and hasattr(settings, "agent"):
            mcp_config = getattr(settings.agent, "mcp", {}) or {}

        if mcp_config:
            return await load_mcp_tools(mcp_config)
    except Exception:
        pass

    return registry


def get_default_registry() -> ToolRegistry:
    """获取默认的 tool 注册表"""
    from .tools import (
        register_system_tools,
        register_detection_tools,
        register_log_tools,
        register_file_tools,
        register_command_tools,
    )

    registry = ToolRegistry()
    register_system_tools(registry)
    register_detection_tools(registry)
    register_log_tools(registry)
    register_file_tools(registry)
    register_command_tools(registry)
    return registry
