"""命令工具 - 白名单模式"""

import re
from typing import Any, Dict, FrozenSet, List, Set

from ..tool_registry import AgentToolResult, BaseTool, ToolRegistry, ToolStatus


SAFE_COMMANDS: FrozenSet[str] = frozenset(
    {
        "ls",
        "pwd",
        "whoami",
        "id",
        "hostname",
        "date",
        "cal",
        "uptime",
        "df",
        "du",
        "free",
        "top",
        "ps",
        "pidof",
        "pgrep",
        "kill",
        "killall",
        "cat",
        "head",
        "tail",
        "less",
        "more",
        "wc",
        "sort",
        "uniq",
        "grep",
        "awk",
        "sed",
        "cut",
        "tr",
        "find",
        "locate",
        "which",
        "whereis",
        "type",
        "lsblk",
        "lspci",
        "lscpu",
        "lsmod",
        "lsattr",
        "file",
        "stat",
        "md5sum",
        "sha1sum",
        "sha256sum",
        "sum",
        "cksum",
        "tar",
        "gzip",
        "gunzip",
        "bzip2",
        "bunzip2",
        "xz",
        "unxz",
        "zip",
        "unzip",
        "cp",
        "mv",
        "mkdir",
        "rmdir",
        "chmod",
        "chown",
        "chgrp",
        "touch",
        "ln",
        "netstat",
        "ss",
        "ip",
        "ifconfig",
        "route",
        "arp",
        "ping",
        "traceroute",
        "nslookup",
        "dig",
        "curl",
        "wget",
        "ssh",
        "scp",
        "rsync",
        "systemctl",
        "service",
        "journalctl",
        "crontab",
        "at",
        "useradd",
        "userdel",
        "usermod",
        "groupadd",
        "groupdel",
        "passwd",
        "sudo",
        "su",
        "env",
        "export",
        "echo",
        "printf",
        "test",
        "true",
        "false",
        "yes",
        "seq",
        "dirname",
        "basename",
        "path",
        "realpath",
        "xargs",
        "nice",
        "nohup",
        "timeout",
        "time",
    }
)

SAFE_PATTERN_PREFIXES: FrozenSet[str] = frozenset(
    {
        "ls ",
        "ls -",
        "lsblk",
        "lspci",
        "lscpu",
        "ps ",
        "ps -",
        "cat ",
        "head ",
        "tail ",
        "grep ",
        "awk ",
        "sed ",
        "cut ",
        "wc ",
        "find ",
        "stat ",
        "file ",
        "df -",
        "du -",
        "free -",
        "uptime",
        "hostname",
        "date",
        "tar -",
        "gzip",
        "gunzip",
        "bzip2",
        "bunzip2",
        "zip",
        "unzip",
        "chmod ",
        "chown ",
        "chgrp ",
        "cp ",
        "mv ",
        "mkdir ",
        "rmdir ",
        "netstat -",
        "ss -",
        "ip ",
        "ifconfig",
        "ping ",
        "curl ",
        "wget ",
        "systemctl ",
        "journalctl ",
        "crontab ",
    }
)

SAFE_PATTERNS: List[re.Pattern] = [
    re.compile(r"^ls(\s+-?[a-zA-Z]+)*\s+(/[a-zA-Z0-9_/.-]*)?$"),
    re.compile(r"^pwd$"),
    re.compile(r"^whoami$"),
    re.compile(r"^id(\s+[a-zA-Z0-9_]+)?$"),
    re.compile(r"^hostname$"),
    re.compile(r"^date$"),
    re.compile(r"^uptime$"),
    re.compile(r"^df(\s+-?[a-zA-Z]+)*\s*([/a-zA-Z0-9_]*)?$"),
    re.compile(r"^du(\s+-?[a-zA-Z]+)*\s*[a-zA-Z0-9_/.-]*$"),
    re.compile(r"^free(\s+-?[a-zA-Z]+)*$"),
    re.compile(r"^ps(\s+-?[a-zA-Z]+)*$"),
    re.compile(r"^cat\s+[a-zA-Z0-9_/.-]+$"),
    re.compile(r"^head(\s+-?[ncm])?\s+[a-zA-Z0-9_/.-]+$"),
    re.compile(r"^tail(\s+-?[ncm])?\s+[a-zA-Z0-9_/.-]+$"),
    re.compile(r"^grep\s+.*"),
    re.compile(r"^awk\s+.*"),
    re.compile(r"^sed\s+.*"),
    re.compile(r"^find\s+.*"),
    re.compile(r"^stat\s+[a-zA-Z0-9_/.-]+$"),
    re.compile(r"^file\s+[a-zA-Z0-9_/.-]+$"),
    re.compile(r"^tar\s+-[cxtvzf]+.*"),
    re.compile(r"^chmod\s+[0-7][0-7][0-7]\s+[a-zA-Z0-9_/.-]+$"),
    re.compile(r"^chmod\s+[a-z]+[a-z]*\s+[a-zA-Z0-9_/.-]+$"),
    re.compile(r"^cp\s+[a-zA-Z0-9_/.-]+\s+[a-zA-Z0-9_/.-]+$"),
    re.compile(r"^mv\s+[a-zA-Z0-9_/.-]+\s+[a-zA-Z0-9_/.-]+$"),
    re.compile(r"^mkdir\s+-[p]?\s+[a-zA-Z0-9_/.-]+$"),
    re.compile(r"^rmdir\s+[a-zA-Z0-9_/.-]+$"),
    re.compile(r"^rm\s+-[Ii]\s+[a-zA-Z0-9_/.-]+$"),
    re.compile(r"^rm\s+--\s+[a-zA-Z0-9_/.-]+$"),
    re.compile(r"^rm\s+-[rR]\s+[a-zA-Z0-9_/.-]+\s+[a-zA-Z0-9_/.-]+$"),
    re.compile(r"^netstat(\s+-[a-z]+)*\s*$"),
    re.compile(r"^ss(\s+-[a-z]+)*\s*$"),
    re.compile(r"^ip\s+(addr|route|link|neighbor|rule)\s+.*"),
    re.compile(r"^systemctl\s+(status|start|stop|restart|enable|disable)\s+.*"),
    re.compile(r"^journalctl(\s+-[a-zA-Z]+)*(\s+--since|--until)?\s*.*"),
    re.compile(r"^crontab\s+(-l|-r|-e)?\s*$"),
]


class CommandTool(BaseTool):
    """命令执行工具 - 白名单模式"""

    @property
    def name(self) -> str:
        return "execute_command"

    @property
    def description(self) -> str:
        return "在远程主机上执行预定义的安全命令"

    @property
    def parameters(self) -> list:
        return [
            {"name": "command", "type": "string", "description": "要执行的命令"},
        ]

    def _is_command_allowed(self, command: str) -> bool:
        cmd_stripped = command.strip()

        if not cmd_stripped:
            return False

        if cmd_stripped in SAFE_COMMANDS:
            return True

        parts = cmd_stripped.split()
        if parts and parts[0] in SAFE_COMMANDS:
            return True

        for prefix in SAFE_PATTERN_PREFIXES:
            if cmd_stripped.startswith(prefix):
                return True

        for pattern in SAFE_PATTERNS:
            if pattern.match(cmd_stripped):
                return True

        return False

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        command = parameters.get("command")
        if not command:
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.ERROR,
                error="command is required",
            )

        if not self._is_command_allowed(command):
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.ERROR,
                error=f"Command not in whitelist: {command[:50]}...",
            )

        try:
            result = await manager.execute_command(command)
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS
                if result.exit_code == 0
                else ToolStatus.ERROR,
                output=result.output,
                error=None
                if result.exit_code == 0
                else f"Exit code: {result.exit_code}",
                metadata={
                    "exit_code": result.exit_code,
                    "command": command,
                },
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class WhitelistedCommandTool(BaseTool):
    """预定义白名单命令工具"""

    _COMMANDS: List[Dict[str, str]] = [
        {
            "name": "list_home",
            "command": "ls -la ~",
            "description": "列出用户主目录内容",
        },
        {"name": "list_root", "command": "ls -la /", "description": "列出根目录内容"},
        {"name": "disk_usage", "command": "df -h", "description": "显示磁盘使用情况"},
        {
            "name": "memory_status",
            "command": "free -h",
            "description": "显示内存使用情况",
        },
        {"name": "system_load", "command": "uptime", "description": "显示系统负载"},
        {"name": "process_tree", "command": "ps auxf", "description": "显示进程树"},
        {
            "name": "top_processes",
            "command": "ps aux --sort=-%cpu | head -20",
            "description": "显示 CPU 占用最高的进程",
        },
        {
            "name": "network_connections",
            "command": "ss -tunap",
            "description": "显示网络连接",
        },
        {
            "name": "open_ports",
            "command": "netstat -tlnp 2>/dev/null || ss -tlnp",
            "description": "显示监听端口",
        },
        {"name": "recent_logins", "command": "last -20", "description": "显示最近登录"},
        {
            "name": "failed_logins",
            "command": "grep -i failed /var/log/auth.log 2>/dev/null | tail -10",
            "description": "显示失败登录尝试",
        },
        {
            "name": "systemd_services",
            "command": "systemctl list-units --type=service --state=running",
            "description": "显示运行中的服务",
        },
        {
            "name": "enabled_services",
            "command": "systemctl list-unit-files --state=enabled",
            "description": "显示已启用的服务",
        },
        {
            "name": "cron_jobs",
            "command": "crontab -l 2>/dev/null",
            "description": "显示当前用户的计划任务",
        },
        {
            "name": "system_crons",
            "command": "cat /etc/crontab 2>/dev/null",
            "description": "显示系统计划任务",
        },
        {
            "name": "passwd_file",
            "command": "cat /etc/passwd | tail -20",
            "description": "显示用户账户",
        },
        {
            "name": "sudoers",
            "command": "sudo -l 2>/dev/null",
            "description": "显示 sudo 权限",
        },
        {
            "name": "selinux_status",
            "command": "getenforce 2>/dev/null || echo 'SELinux not installed'",
            "description": "显示 SELinux 状态",
        },
        {
            "name": "firewall_rules",
            "command": "sudo iptables -L -n 2>/dev/null | head -30",
            "description": "显示防火墙规则",
        },
        {
            "name": "system_logs",
            "command": "journalctl -n 50 --no-pager",
            "description": "显示系统日志",
        },
        {
            "name": "kernel_messages",
            "command": "dmesg | tail -50",
            "description": "显示内核消息",
        },
    ]

    @property
    def name(self) -> str:
        return "whitelisted_commands"

    @property
    def description(self) -> str:
        return "列出所有可用的白名单命令"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        return AgentToolResult(
            tool_name=self.name,
            status=ToolStatus.SUCCESS,
            output=self._COMMANDS,
            metadata={"count": len(self._COMMANDS)},
        )


class ExecuteWhitelistedTool(BaseTool):
    """执行预定义白名单命令"""

    _COMMAND_MAP: Dict[str, str] = {
        "list_home": "ls -la ~",
        "list_root": "ls -la /",
        "disk_usage": "df -h",
        "memory_status": "free -h",
        "system_load": "uptime",
        "process_tree": "ps auxf",
        "top_processes": "ps aux --sort=-%cpu | head -20",
        "network_connections": "ss -tunap",
        "open_ports": "netstat -tlnp 2>/dev/null || ss -tlnp",
        "recent_logins": "last -20",
        "failed_logins": "grep -i failed /var/log/auth.log 2>/dev/null | tail -10",
        "systemd_services": "systemctl list-units --type=service --state=running",
        "enabled_services": "systemctl list-unit-files --state=enabled",
        "cron_jobs": "crontab -l 2>/dev/null",
        "system_crons": "cat /etc/crontab 2>/dev/null",
        "passwd_file": "cat /etc/passwd | tail -20",
        "sudoers": "sudo -l 2>/dev/null",
        "selinux_status": "getenforce 2>/dev/null || echo 'SELinux not installed'",
        "firewall_rules": "sudo iptables -L -n 2>/dev/null | head -30",
        "system_logs": "journalctl -n 50 --no-pager",
        "kernel_messages": "dmesg | tail -50",
    }

    @property
    def name(self) -> str:
        return "run_whitelisted_command"

    @property
    def description(self) -> str:
        return "执行预定义的白名单命令"

    @property
    def parameters(self) -> list:
        return [
            {"name": "command_key", "type": "string", "description": "命令标识符"},
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

        command_key = parameters.get("command_key")
        if not command_key:
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.ERROR,
                error="command_key is required",
            )

        command = self._COMMAND_MAP.get(command_key)
        if not command:
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.ERROR,
                error=f"Unknown command key: {command_key}",
            )

        try:
            result = await manager.execute_command(command)
            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS
                if result.exit_code == 0
                else ToolStatus.ERROR,
                output=result.output,
                error=None
                if result.exit_code == 0
                else f"Exit code: {result.exit_code}",
                metadata={
                    "exit_code": result.exit_code,
                    "command_key": command_key,
                    "command": command,
                },
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


def register_command_tools(registry: ToolRegistry) -> None:
    registry.register(CommandTool())
    registry.register(WhitelistedCommandTool())
    registry.register(ExecuteWhitelistedTool())
