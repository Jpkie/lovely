"""Agent Tools 包"""

from ..tool_registry import ToolRegistry

from .system_tools import register_system_tools
from .detection_tools import register_detection_tools
from .log_tools import register_log_tools
from .file_tools import register_file_tools
from .command_tools import register_command_tools
from .remediation_tools import register_remediation_tools

__all__ = [
    "register_system_tools",
    "register_detection_tools",
    "register_log_tools",
    "register_file_tools",
    "register_command_tools",
    "register_remediation_tools",
]
