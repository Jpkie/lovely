"""文件工具 - 复用 file_analysis"""

from typing import Any, Dict

from ..tool_registry import AgentToolResult, BaseTool, ToolRegistry, ToolStatus


class FileAnalysisTool(BaseTool):
    """文件安全分析"""

    @property
    def name(self) -> str:
        return "file_analysis"

    @property
    def description(self) -> str:
        return "分析指定文件的安全属性，包括权限、哈希、风险指标等"

    @property
    def parameters(self) -> list:
        return [
            {"name": "path", "type": "string", "description": "文件路径"},
        ]

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager
        from app.services.file_analysis import sftp_file_analysis

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        path = parameters.get("path")
        if not path:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="path is required"
            )

        try:
            result = await sftp_file_analysis(manager, path)
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output=result.model_dump(),
                metadata={
                    "path": path,
                    "risk_level": result.risk_level,
                    "risk_indicator_count": len(result.risk_indicators),
                },
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class ListDirectoryTool(BaseTool):
    """列出目录内容"""

    @property
    def name(self) -> str:
        return "list_directory"

    @property
    def description(self) -> str:
        return "列出指定目录的文件和子目录"

    @property
    def parameters(self) -> list:
        return [
            {
                "name": "path",
                "type": "string",
                "description": "目录路径",
                "default": "/",
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

        path = parameters.get("path", "/")

        try:
            files = await manager.list_sftp_files(path)
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output=[f.model_dump() for f in files],
                metadata={"path": path, "count": len(files)},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class ReadFileTool(BaseTool):
    """读取文件内容"""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "读取远程文件内容（文本文件）"

    @property
    def parameters(self) -> list:
        return [
            {"name": "path", "type": "string", "description": "文件路径"},
            {
                "name": "max_size",
                "type": "integer",
                "description": "最大读取大小(字节)",
                "default": 65536,
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

        path = parameters.get("path")
        if not path:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="path is required"
            )

        try:
            content_bytes = await manager.read_sftp_file(path)
            max_size = parameters.get("max_size", 65536)
            content = content_bytes[:max_size].decode("utf-8", errors="replace")
            truncated = len(content_bytes) > max_size

            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output={
                    "content": content,
                    "truncated": truncated,
                    "total_size": len(content_bytes),
                },
                metadata={
                    "path": path,
                    "read_size": len(content),
                    "truncated": truncated,
                },
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class GetFileDetailsTool(BaseTool):
    """获取文件详细信息"""

    @property
    def name(self) -> str:
        return "get_file_details"

    @property
    def description(self) -> str:
        return "获取文件的详细信息，包括所有者、权限、时间戳等"

    @property
    def parameters(self) -> list:
        return [
            {"name": "path", "type": "string", "description": "文件路径"},
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

        path = parameters.get("path")
        if not path:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="path is required"
            )

        try:
            result = await manager.get_file_details(path)
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output=result.model_dump(),
                metadata={"path": path},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


def register_file_tools(registry: ToolRegistry) -> None:
    registry.register(FileAnalysisTool())
    registry.register(ListDirectoryTool())
    registry.register(ReadFileTool())
    registry.register(GetFileDetailsTool())
