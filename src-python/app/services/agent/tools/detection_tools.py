"""检测工具 - 复用 detection_manager"""

from typing import Any, Dict

from ..tool_registry import AgentToolResult, BaseTool, ToolRegistry, ToolStatus


class PortScanTool(BaseTool):
    """端口扫描检测"""

    @property
    def name(self) -> str:
        return "detect_port_scan"

    @property
    def description(self) -> str:
        return "扫描主机开放端口并识别服务"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager
        from app.services.detection_manager import detect_port_scan

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await detect_port_scan(manager)
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output=result.model_dump(),
                metadata={
                    "risk_level": result.risk_level,
                    "port_count": result.total_open,
                },
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class UserAuditTool(BaseTool):
    """用户审计"""

    @property
    def name(self) -> str:
        return "detect_user_audit"

    @property
    def description(self) -> str:
        return "审计系统用户，发现特权用户和空密码用户"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager
        from app.services.detection_manager import detect_user_audit

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await detect_user_audit(manager)
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output=result.model_dump(),
                metadata={"risk_level": result.risk_level},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class BackdoorScanTool(BaseTool):
    """后门检测"""

    @property
    def name(self) -> str:
        return "detect_backdoor"

    @property
    def description(self) -> str:
        return "检测计划任务、启动项和 SSH authorized_keys 中的可疑项"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager
        from app.services.detection_manager import detect_backdoor

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await detect_backdoor(manager)
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output=result.model_dump(),
                metadata={"risk_level": result.risk_level},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class ProcessAnalysisTool(BaseTool):
    """进程分析"""

    @property
    def name(self) -> str:
        return "detect_process"

    @property
    def description(self) -> str:
        return "分析系统进程，发现可疑进程和高资源占用进程"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager
        from app.services.detection_manager import detect_process_analysis

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await detect_process_analysis(manager)
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output=result.model_dump(),
                metadata={"risk_level": result.risk_level},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class FilePermissionTool(BaseTool):
    """文件权限检测"""

    @property
    def name(self) -> str:
        return "detect_file_permission"

    @property
    def description(self) -> str:
        return "检测 SUID 文件和敏感文件权限问题"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager
        from app.services.detection_manager import detect_file_permission

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await detect_file_permission(manager)
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output=result.model_dump(),
                metadata={"risk_level": result.risk_level},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class SSHAuditTool(BaseTool):
    """SSH 审计"""

    @property
    def name(self) -> str:
        return "detect_ssh_audit"

    @property
    def description(self) -> str:
        return "审计 SSH 配置安全性"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager
        from app.services.detection_manager import detect_ssh_audit

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await detect_ssh_audit(manager)
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output=result.model_dump(),
                metadata={"risk_level": result.risk_level},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class LogAnalysisTool(BaseTool):
    """日志分析检测"""

    @property
    def name(self) -> str:
        return "detect_log"

    @property
    def description(self) -> str:
        return "分析日志文件，发现失败登录尝试等安全事件"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager
        from app.services.detection_manager import detect_log_analysis

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await detect_log_analysis(manager)
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output=result.model_dump(),
                metadata={"risk_level": result.risk_level},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class FirewallCheckTool(BaseTool):
    """防火墙检查"""

    @property
    def name(self) -> str:
        return "detect_firewall"

    @property
    def description(self) -> str:
        return "检查防火墙状态"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager
        from app.services.detection_manager import detect_firewall_check

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await detect_firewall_check(manager)
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output=result.model_dump(),
                metadata={"risk_level": result.risk_level},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class CpuTestTool(BaseTool):
    """CPU 测试"""

    @property
    def name(self) -> str:
        return "detect_cpu"

    @property
    def description(self) -> str:
        return "获取 CPU 信息和使用率"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager
        from app.services.detection_manager import detect_cpu_test

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await detect_cpu_test(manager)
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output=result.model_dump(),
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class MemoryTestTool(BaseTool):
    """内存测试"""

    @property
    def name(self) -> str:
        return "detect_memory"

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
        from app.services.detection_manager import detect_memory_test

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await detect_memory_test(manager)
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output=result.model_dump(),
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class DiskTestTool(BaseTool):
    """磁盘测试"""

    @property
    def name(self) -> str:
        return "detect_disk"

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
        from app.services.detection_manager import detect_disk_test

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await detect_disk_test(manager)
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output=result.model_dump(),
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class NetworkTestTool(BaseTool):
    """网络测试"""

    @property
    def name(self) -> str:
        return "detect_network"

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
        from app.services.detection_manager import detect_network_test

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await detect_network_test(manager)
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output=result.model_dump(),
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


def register_detection_tools(registry: ToolRegistry) -> None:
    registry.register(PortScanTool())
    registry.register(UserAuditTool())
    registry.register(BackdoorScanTool())
    registry.register(ProcessAnalysisTool())
    registry.register(FilePermissionTool())
    registry.register(SSHAuditTool())
    registry.register(LogAnalysisTool())
    registry.register(FirewallCheckTool())
    registry.register(CpuTestTool())
    registry.register(MemoryTestTool())
    registry.register(DiskTestTool())
    registry.register(NetworkTestTool())
