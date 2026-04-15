"""MCP Registry - MCP 工具注册与管理

职责:
  - MCPRegistry: 管理 MCP 适配器和工具定义
  - get_mcp_registry(): 获取全局单例 MCP registry
  - get_enabled_mcp_tools(): 获取已启用的 MCP 工具列表（供 /agent/tools 展示用）
  - load_mcp_tools_if_enabled(): 根据设置加载 MCP 工具（供 runtime registry 合并用）

注意:
  - MCP 未启用时系统照常运行
  - get_enabled_mcp_tools() 从全局 registry 读取，
    load_mcp_tools_if_enabled() 从 settings 重新初始化
"""

from typing import Any, Dict, List, Optional

from .mcp_adapter import MCPAdapter, MCPTool


class MCPRegistry:
    """MCP 工具注册表"""

    def __init__(self):
        self._adapters: Dict[str, MCPAdapter] = {}
        self._tools: Dict[str, MCPTool] = {}

    def register_adapter(self, name: str, adapter: MCPAdapter) -> None:
        self._adapters[name] = adapter

    def get_adapter(self, name: str) -> Optional[MCPAdapter]:
        return self._adapters.get(name)

    def list_adapters(self) -> List[str]:
        return list(self._adapters.keys())

    def register_tool(self, tool: MCPTool) -> None:
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[MCPTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[MCPTool]:
        return list(self._tools.values())

    def clear(self) -> None:
        self._tools.clear()


_mcp_registry: Optional[MCPRegistry] = None


def get_mcp_registry() -> MCPRegistry:
    global _mcp_registry
    if _mcp_registry is None:
        _mcp_registry = MCPRegistry()
    return _mcp_registry


def get_enabled_mcp_tools() -> List[Dict[str, Any]]:
    """获取已启用的 MCP 工具列表"""
    try:
        from app.services.settings import load_settings

        settings = load_settings()
        agent_settings = settings.agent

        if not agent_settings or not getattr(agent_settings, "mcp_enabled", False):
            return []

        registry = get_mcp_registry()
        tools = registry.list_tools()

        return [
            {
                "id": f"mcp_{t.name}",
                "name": t.name,
                "description": t.description,
                "source": "mcp",
                "risk_level": "medium",
                "enabled": t.enabled,
                "server_name": t.server_name,
            }
            for t in tools
        ]
    except Exception:
        return []


async def load_mcp_tools_if_enabled(settings: Any) -> MCPRegistry:
    """根据设置加载 MCP 工具（如启用），返回 MCPRegistry 实例

    与 tool_registry.load_mcp_tools_if_enabled 职责不同：
    - 本函数初始化 MCPRegistry（管理 adapter + tool definitions）
    - tool_registry 版本返回 ToolRegistry（管理 executors，供实际执行用）
    """
    registry = get_mcp_registry()

    try:
        mcp_enabled = False
        mcp_config: Dict[str, Any] = {}

        if hasattr(settings, "mcp_enabled"):
            mcp_enabled = settings.mcp_enabled
        elif hasattr(settings, "agent") and settings.agent:
            mcp_enabled = getattr(settings.agent, "mcp_enabled", False)

        if not mcp_enabled:
            return registry

        if hasattr(settings, "mcp") and settings.mcp:
            mcp_config = (
                dict(settings.mcp)
                if not isinstance(settings.mcp, dict)
                else settings.mcp
            )
        elif hasattr(settings, "agent") and settings.agent:
            mcp_config = getattr(settings.agent, "mcp", {}) or {}

        if not mcp_config:
            return registry

        adapter = MCPAdapter.from_config(mcp_config)
        if adapter.enabled:
            registry.register_adapter("default", adapter)
            if await adapter.initialize():
                tools = await adapter.list_tools()
                for tool in tools:
                    registry.register_tool(tool)

    except Exception:
        pass

    return registry
