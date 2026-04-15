"""日志工具 - 复用 log_analysis"""

from typing import Any, Dict, Optional

from ..tool_registry import AgentToolResult, BaseTool, ToolRegistry, ToolStatus


class ReadSystemLogTool(BaseTool):
    """读取系统日志"""

    @property
    def name(self) -> str:
        return "read_system_log"

    @property
    def description(self) -> str:
        return "读取指定路径的系统日志文件"

    @property
    def parameters(self) -> list:
        return [
            {"name": "log_path", "type": "string", "description": "日志文件路径"},
            {"name": "page", "type": "integer", "description": "页码", "default": 1},
            {
                "name": "page_size",
                "type": "integer",
                "description": "每页行数",
                "default": 100,
            },
            {
                "name": "filter_text",
                "type": "string",
                "description": "过滤文本",
                "default": None,
            },
            {
                "name": "date_filter",
                "type": "string",
                "description": "日期过滤",
                "default": None,
            },
        ]

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager
        from app.services.log_analysis import read_system_log

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        log_path = parameters.get("log_path")
        if not log_path:
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.ERROR,
                error="log_path is required",
            )

        try:
            result = await read_system_log(
                manager,
                log_path=log_path,
                page=parameters.get("page", 1),
                page_size=parameters.get("page_size", 100),
                filter_text=parameters.get("filter_text"),
                date_filter=parameters.get("date_filter"),
            )
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output=result.model_dump(),
                metadata={
                    "log_path": log_path,
                    "total_count": result.total_count,
                    "highlighted_count": result.highlighted_count,
                },
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class ReadJournalctlLogTool(BaseTool):
    """读取 journalctl 日志"""

    @property
    def name(self) -> str:
        return "read_journalctl_log"

    @property
    def description(self) -> str:
        return "读取 systemd journal 日志"

    @property
    def parameters(self) -> list:
        return [
            {"name": "page", "type": "integer", "description": "页码", "default": 1},
            {
                "name": "page_size",
                "type": "integer",
                "description": "每页行数",
                "default": 100,
            },
            {
                "name": "unit",
                "type": "string",
                "description": "服务单元名称",
                "default": None,
            },
            {
                "name": "filter_text",
                "type": "string",
                "description": "过滤文本",
                "default": None,
            },
            {
                "name": "since",
                "type": "string",
                "description": "开始时间",
                "default": None,
            },
            {
                "name": "until",
                "type": "string",
                "description": "结束时间",
                "default": None,
            },
        ]

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager
        from app.services.log_analysis import read_journalctl_log

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await read_journalctl_log(
                manager,
                page=parameters.get("page", 1),
                page_size=parameters.get("page_size", 100),
                unit=parameters.get("unit"),
                filter_text=parameters.get("filter_text"),
                since=parameters.get("since"),
                until=parameters.get("until"),
            )
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output=result.model_dump(),
                metadata={
                    "total_count": result.total_count,
                    "highlighted_count": result.highlighted_count,
                },
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class ListLogFilesTool(BaseTool):
    """列出日志文件"""

    @property
    def name(self) -> str:
        return "list_log_files"

    @property
    def description(self) -> str:
        return "列出系统中可用的日志文件"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager
        from app.services.log_analysis import list_log_files

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await list_log_files(manager)
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output=[r.model_dump() for r in result],
                metadata={"count": len(result)},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class GetLogFileInfoTool(BaseTool):
    """获取日志文件信息"""

    @property
    def name(self) -> str:
        return "get_log_file_info"

    @property
    def description(self) -> str:
        return "获取指定日志文件的详细信息"

    @property
    def parameters(self) -> list:
        return [
            {"name": "log_path", "type": "string", "description": "日志文件路径"},
        ]

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager
        from app.services.log_analysis import get_log_file_info

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        log_path = parameters.get("log_path")
        if not log_path:
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.ERROR,
                error="log_path is required",
            )

        try:
            result = await get_log_file_info(manager, log_path)
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS if result.readable else ToolStatus.ERROR,
                output=result.model_dump(),
                metadata={"log_path": log_path, "readable": result.readable},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


def register_log_tools(registry: ToolRegistry) -> None:
    registry.register(ReadSystemLogTool())
    registry.register(ReadJournalctlLogTool())
    registry.register(ListLogFilesTool())
    registry.register(GetLogFileInfoTool())
