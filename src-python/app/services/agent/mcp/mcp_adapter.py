"""MCP 适配器 - 处理与 MCP Server 的通信"""

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, AsyncIterator
import urllib.request
import urllib.error


class MCPConnectionStatus(str, Enum):
    """MCP 连接状态"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class MCPTransport(str, Enum):
    """MCP 传输类型"""

    HTTP = "http"
    STDIO = "stdio"
    WEBSOCKET = "websocket"


@dataclass
class MCPTool:
    """MCP Tool 定义"""

    name: str
    description: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    server_name: str = ""
    server_id: str = ""
    enabled: bool = True


@dataclass
class MCPToolCall:
    """MCP Tool 调用请求"""

    tool_name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None


@dataclass
class MCPToolResult:
    """MCP Tool 调用结果"""

    call_id: str
    tool_name: str
    success: bool
    content: Optional[Any] = None
    error: Optional[str] = None
    is_error: bool = False


class BaseMCPTransport(ABC):
    """MCP 传输层基类"""

    @abstractmethod
    async def connect(self) -> bool:
        """建立连接"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """断开连接"""
        pass

    @abstractmethod
    async def send_request(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发送请求"""
        pass

    @abstractmethod
    async def send_notification(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> None:
        """发送通知（无响应）"""
        pass

    @property
    @abstractmethod
    def status(self) -> MCPConnectionStatus:
        """获取连接状态"""
        pass


class HTTPMCPTransport(BaseMCPTransport):
    """HTTP MCP 传输层"""

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        api_key: Optional[str] = None,
    ):
        self.url = url.rstrip("/")
        self.headers = headers or {}
        self.timeout = timeout
        self._status = MCPConnectionStatus.DISCONNECTED

        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    @property
    def status(self) -> MCPConnectionStatus:
        return self._status

    async def connect(self) -> bool:
        self._status = MCPConnectionStatus.CONNECTING
        try:
            await self._health_check()
            self._status = MCPConnectionStatus.CONNECTED
            return True
        except Exception:
            self._status = MCPConnectionStatus.ERROR
            return False

    async def disconnect(self) -> None:
        self._status = MCPConnectionStatus.DISCONNECTED

    async def send_request(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if self._status != MCPConnectionStatus.CONNECTED:
            raise RuntimeError(f"MCP not connected: {self._status}")

        payload = {
            "jsonrpc": "2.0",
            "id": str(datetime.utcnow().timestamp()),
            "method": method,
            "params": params or {},
        }

        data = json.dumps(payload).encode("utf-8")
        headers = {**self.headers, "Content-Type": "application/json"}
        req = urllib.request.Request(
            self.url, data=data, headers=headers, method="POST"
        )

        loop = asyncio.get_event_loop()
        try:
            with await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=self.timeout)
            ) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if "error" in result:
                    raise RuntimeError(f"MCP error: {result['error']}")
                return result.get("result", {})
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP error {e.code}: {e.read().decode()}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"URL error: {e.reason}")

    async def send_notification(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> None:
        if self._status != MCPConnectionStatus.CONNECTED:
            return

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
        }

        data = json.dumps(payload).encode("utf-8")
        headers = {**self.headers, "Content-Type": "application/json"}
        req = urllib.request.Request(
            self.url, data=data, headers=headers, method="POST"
        )

        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=self.timeout)
            )
        except Exception:
            pass

    async def _health_check(self) -> None:
        await self.send_request("ping")


class MCPAdapter:
    """MCP 适配器 - 统一接口

    第一版预留实现，MCP 未配置时系统照常运行。
    """

    def __init__(
        self,
        enabled: bool = False,
        transport_type: MCPTransport = MCPTransport.HTTP,
        server_url: Optional[str] = None,
        server_config: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
    ):
        self.enabled = enabled
        self.transport_type = transport_type
        self.server_url = server_url
        self.server_config = server_config or {}
        self.api_key = api_key

        self._transport: Optional[BaseMCPTransport] = None
        self._tools: Dict[str, MCPTool] = {}
        self._status = MCPConnectionStatus.DISCONNECTED

    @property
    def status(self) -> MCPConnectionStatus:
        return self._status

    @property
    def tools(self) -> Dict[str, MCPTool]:
        return self._tools

    def is_available(self) -> bool:
        """检查 MCP 是否可用"""
        return self.enabled and self._status == MCPConnectionStatus.CONNECTED

    async def initialize(self) -> bool:
        """初始化 MCP 连接"""
        if not self.enabled:
            return False

        if not self.server_url:
            return False

        try:
            if self.transport_type == MCPTransport.HTTP:
                self._transport = HTTPMCPTransport(
                    url=self.server_url,
                    api_key=self.api_key,
                    timeout=self.server_config.get("timeout", 30),
                )
            else:
                return False

            connected = await self._transport.connect()
            if connected:
                self._status = MCPConnectionStatus.CONNECTED
                await self._discover_tools()
                return True
            return False
        except Exception as e:
            self._status = MCPConnectionStatus.ERROR
            return False

    async def shutdown(self) -> None:
        """关闭 MCP 连接"""
        if self._transport:
            await self._transport.disconnect()
        self._status = MCPConnectionStatus.DISCONNECTED
        self._tools.clear()

    async def list_tools(self) -> List[MCPTool]:
        """列出可用工具"""
        if not self.is_available():
            return []
        return list(self._tools.values())

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> MCPToolResult:
        """调用 MCP Tool"""
        if not self.is_available():
            return MCPToolResult(
                call_id="",
                tool_name=tool_name,
                success=False,
                error="MCP not available",
                is_error=True,
            )

        if tool_name not in self._tools:
            return MCPToolResult(
                call_id="",
                tool_name=tool_name,
                success=False,
                error=f"Tool not found: {tool_name}",
                is_error=True,
            )

        call_id = f"call_{datetime.utcnow().timestamp()}"

        try:
            result = await self._transport.send_request(
                "tools/call",
                {
                    "name": tool_name,
                    "arguments": arguments,
                },
            )
            return MCPToolResult(
                call_id=call_id,
                tool_name=tool_name,
                success=True,
                content=result,
            )
        except Exception as e:
            return MCPToolResult(
                call_id=call_id,
                tool_name=tool_name,
                success=False,
                error=str(e),
                is_error=True,
            )

    async def _discover_tools(self) -> None:
        """发现 MCP 服务提供的工具"""
        try:
            result = await self._transport.send_request("tools/list")
            tools_data = result.get("tools", [])

            for tool_data in tools_data:
                tool = MCPTool(
                    name=tool_data.get("name", ""),
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {}),
                    server_name=self.server_config.get("name", "unknown"),
                    server_id=self.server_config.get("id", ""),
                )
                if tool.name:
                    self._tools[tool.name] = tool
        except Exception:
            pass

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "MCPAdapter":
        """从配置创建 MCP 适配器"""
        return cls(
            enabled=config.get("enabled", False),
            transport_type=MCPTransport(config.get("transport", "http")),
            server_url=config.get("server_url"),
            server_config=config.get("server_config", {}),
            api_key=config.get("api_key"),
        )

    def to_config(self) -> Dict[str, Any]:
        """导出配置"""
        return {
            "enabled": self.enabled,
            "transport": self.transport_type.value,
            "server_url": self.server_url,
            "server_config": self.server_config,
            "api_key": self.api_key,
        }
