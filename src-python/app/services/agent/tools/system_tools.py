"""系统信息工具"""

from typing import Any, Dict

from ..tool_registry import AgentToolResult, BaseTool, ToolRegistry, ToolStatus


class HostnameTool(BaseTool):
    """获取主机名"""

    @property
    def name(self) -> str:
        return "hostname"

    @property
    def description(self) -> str:
        return "获取远程主机的主机名"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await manager.execute_command("hostname")
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS
                if result.exit_code == 0
                else ToolStatus.ERROR,
                output=result.output.strip() if result.exit_code == 0 else None,
                error=result.output if result.exit_code != 0 else None,
                metadata={"exit_code": result.exit_code},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class UptimeTool(BaseTool):
    """获取系统运行时间"""

    @property
    def name(self) -> str:
        return "uptime"

    @property
    def description(self) -> str:
        return "获取系统运行时间和负载信息"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await manager.execute_command("uptime")
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS
                if result.exit_code == 0
                else ToolStatus.ERROR,
                output=result.output.strip() if result.exit_code == 0 else None,
                error=result.output if result.exit_code != 0 else None,
                metadata={"exit_code": result.exit_code},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class UnameTool(BaseTool):
    """获取系统信息"""

    @property
    def name(self) -> str:
        return "uname"

    @property
    def description(self) -> str:
        return "获取操作系统名称和版本信息"

    @property
    def parameters(self) -> list:
        return [{"name": "all", "type": "boolean", "description": "显示所有信息"}]

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            flag = "-a" if parameters.get("all") else ""
            result = await manager.execute_command(f"uname {flag}")
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS
                if result.exit_code == 0
                else ToolStatus.ERROR,
                output=result.output.strip() if result.exit_code == 0 else None,
                error=result.output if result.exit_code != 0 else None,
                metadata={"exit_code": result.exit_code},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class CpuInfoTool(BaseTool):
    """获取 CPU 信息"""

    @property
    def name(self) -> str:
        return "cpu_info"

    @property
    def description(self) -> str:
        return "获取 CPU 详细信息"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await manager.execute_command("lscpu")
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS
                if result.exit_code == 0
                else ToolStatus.ERROR,
                output=result.output if result.exit_code == 0 else None,
                error=result.output if result.exit_code != 0 else None,
                metadata={"exit_code": result.exit_code},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class MemoryInfoTool(BaseTool):
    """获取内存信息"""

    @property
    def name(self) -> str:
        return "memory_info"

    @property
    def description(self) -> str:
        return "获取内存使用情况"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await manager.execute_command("free -h")
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS
                if result.exit_code == 0
                else ToolStatus.ERROR,
                output=result.output if result.exit_code == 0 else None,
                error=result.output if result.exit_code != 0 else None,
                metadata={"exit_code": result.exit_code},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class DiskInfoTool(BaseTool):
    """获取磁盘信息"""

    @property
    def name(self) -> str:
        return "disk_info"

    @property
    def description(self) -> str:
        return "获取磁盘使用情况"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await manager.execute_command("df -h")
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS
                if result.exit_code == 0
                else ToolStatus.ERROR,
                output=result.output if result.exit_code == 0 else None,
                error=result.output if result.exit_code != 0 else None,
                metadata={"exit_code": result.exit_code},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class NetworkInfoTool(BaseTool):
    """获取网络信息"""

    @property
    def name(self) -> str:
        return "network_info"

    @property
    def description(self) -> str:
        return "获取网络接口和连接信息"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await manager.execute_command(
                "ip addr show 2>/dev/null || ifconfig"
            )
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS
                if result.exit_code == 0
                else ToolStatus.ERROR,
                output=result.output if result.exit_code == 0 else None,
                error=result.output if result.exit_code != 0 else None,
                metadata={"exit_code": result.exit_code},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class ProcessListTool(BaseTool):
    """获取进程列表"""

    @property
    def name(self) -> str:
        return "process_list"

    @property
    def description(self) -> str:
        return "获取系统进程列表"

    @property
    def parameters(self) -> list:
        return [
            {
                "name": "top",
                "type": "integer",
                "description": "显示前 N 个进程",
                "default": 20,
            },
            {
                "name": "sort_by",
                "type": "string",
                "description": "排序字段: cpu, mem",
                "default": "cpu",
            },
        ]

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            top = parameters.get("top", 20)
            sort_by = parameters.get("sort_by", "cpu")
            sort_flag = "-%cpu" if sort_by == "cpu" else "-%mem"
            result = await manager.execute_command(
                f"ps aux --sort={sort_flag} | head -n {top + 1}"
            )
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS
                if result.exit_code == 0
                else ToolStatus.ERROR,
                output=result.output if result.exit_code == 0 else None,
                error=result.output if result.exit_code != 0 else None,
                metadata={"exit_code": result.exit_code, "count": top},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


def register_system_tools(registry: ToolRegistry) -> None:
    registry.register(HostnameTool())
    registry.register(UptimeTool())
    registry.register(UnameTool())
    registry.register(CpuInfoTool())
    registry.register(MemoryInfoTool())
    registry.register(DiskInfoTool())
    registry.register(NetworkInfoTool())
    registry.register(ProcessListTool())
