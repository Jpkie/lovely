"""Agent Tool 系统 - 注册中心与结果定义

职责分层:
  - ToolRegistry: 工具注册表，管理所有可用工具和执行器
  - get_default_registry(): 返回内置工具注册表（system/detection/log/file/command）
  - get_runtime_registry(): 返回合并了 MCP tools 的运行时注册表
  - load_mcp_tools_if_enabled(): 根据设置加载 MCP tools（如启用）

执行链路:
  1. orchestrator 持有运行时 registry
  2. executor.execute_plan() 调用 registry.execute_tool()
  3. execute_tool() 优先走 _executors（MCP tools），再走 _tools（内置 BaseTool）
"""

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


def _get_mcp_enabled_and_config(settings: Any) -> tuple[bool, Dict[str, Any]]:
    """从 settings 中提取 mcp_enabled 标志和 mcp_config

    Returns:
        (mcp_enabled, mcp_config)
    """
    mcp_enabled = False
    mcp_config: Dict[str, Any] = {}

    if hasattr(settings, "mcp_enabled"):
        mcp_enabled = settings.mcp_enabled
    elif hasattr(settings, "agent") and settings.agent:
        mcp_enabled = getattr(settings.agent, "mcp_enabled", False)

    if hasattr(settings, "mcp") and settings.mcp:
        mcp_config = (
            dict(settings.mcp) if not isinstance(settings.mcp, dict) else settings.mcp
        )
    elif hasattr(settings, "agent") and settings.agent:
        mcp_config = getattr(settings.agent, "mcp", {}) or {}

    return mcp_enabled, mcp_config


async def load_mcp_tools(mcp_config: Dict[str, Any]) -> ToolRegistry:
    """加载 MCP tools (以 executor 方式注册)

    Args:
        mcp_config: MCP 配置信息

    Returns:
        ToolRegistry: 包含 MCP executor 的注册表
    """
    registry = ToolRegistry()
    try:
        from .mcp import MCPAdapter

        adapter = MCPAdapter.from_config(mcp_config)
        if adapter.enabled and await adapter.initialize():
            tools = await adapter.list_tools()
            for tool in tools:
                tool_name = tool.name

                async def make_executor(t: Any):
                    async def executor(
                        params: Dict[str, Any], ctx: Dict[str, Any]
                    ) -> AgentToolResult:
                        result = await adapter.call_tool(t.name, params)
                        return AgentToolResult(
                            tool_name=t.name,
                            status=ToolStatus.SUCCESS
                            if result.success
                            else ToolStatus.ERROR,
                            output=result.content,
                            error=result.error if result.is_error else None,
                        )

                    return executor

                registry.register_executor(tool_name, await make_executor(tool))
    except Exception:
        pass
    return registry


async def load_mcp_tools_if_enabled(settings: Any) -> ToolRegistry:
    """根据设置加载 MCP tools（如 mcp_enabled=True）

    内部调用 _get_mcp_enabled_and_config 统一读取开关和配置。
    MCP 未启用或无配置时返回空 registry，不抛异常。

    Args:
        settings: AppSettings 实例

    Returns:
        ToolRegistry: MCP tools 注册表（可能为空）
    """
    try:
        mcp_enabled, mcp_config = _get_mcp_enabled_and_config(settings)
        if not mcp_enabled or not mcp_config:
            return ToolRegistry()
        return await load_mcp_tools(mcp_config)
    except Exception:
        pass
    return ToolRegistry()


def get_default_registry() -> ToolRegistry:
    """获取默认的 tool 注册表"""
    from .tools import (
        register_system_tools,
        register_detection_tools,
        register_log_tools,
        register_file_tools,
        register_command_tools,
        register_remediation_tools,
    )

    registry = ToolRegistry()
    register_system_tools(registry)
    register_detection_tools(registry)
    register_log_tools(registry)
    register_file_tools(registry)
    register_command_tools(registry)
    register_remediation_tools(registry)
    return registry


async def get_runtime_registry(settings: Any) -> ToolRegistry:
    """获取运行时 registry，合并 internal + MCP tools

    1. 创建 internal registry
    2. 加载 MCP tools（如启用）
    3. 合并后返回

    Args:
        settings: AppSettings 实例

    Returns:
        ToolRegistry: 合并后的运行时注册表
    """
    registry = get_default_registry()

    try:
        mcp_tools_registry = await load_mcp_tools_if_enabled(settings)
        if mcp_tools_registry and (
            mcp_tools_registry._tools or mcp_tools_registry._executors
        ):
            registry.merge(mcp_tools_registry)
    except Exception:
        pass

    return registry
