"""MCP (Model Context Protocol) 模块

提供 MCP 协议适配和工具注册能力，支持未来扩展外部工具源。

架构说明：
- mcp_adapter.py: MCP 协议适配器，处理与 MCP Server 的通信
- mcp_registry.py: MCP 工具注册表，管理 MCP 加载的工具

第一版预留接口，MCP 未配置时系统照常运行。
"""

from .mcp_adapter import MCPAdapter, MCPTool, MCPConnectionStatus
from .mcp_registry import MCPRegistry, MCPToolDefinition

__all__ = [
    "MCPAdapter",
    "MCPTool",
    "MCPConnectionStatus",
    "MCPRegistry",
    "MCPToolDefinition",
]
