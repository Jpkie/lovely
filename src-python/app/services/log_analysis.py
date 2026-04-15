"""日志分析模块 - 从 Rust log_analysis.rs 迁移"""

import re
from typing import Any, Dict, List, Optional

from app.models.types import LogAnalysisEntry, LogAnalysisOutput, LogFileInfo
from app.services.ssh_manager import SSHManager


# 高亮关键词
HIGHLIGHT_KEYWORDS = [
    "error", "fail", "denied", "refused", "invalid", "unauthorized",
    "critical", "alert", "emergency", "warning", "attack", "breach",
    "malware", "intrusion", "exploit", "vulnerability",
]

# 常见日志文件
COMMON_LOG_FILES: Dict[str, str] = {
    "/var/log/auth.log": "认证日志",
    "/var/log/syslog": "系统日志",
    "/var/log/kern.log": "内核日志",
    "/var/log/dmesg": "启动日志",
    "/var/log/secure": "安全日志",
    "/var/log/messages": "消息日志",
    "/var/log/nginx/access.log": "Nginx访问日志",
    "/var/log/nginx/error.log": "Nginx错误日志",
    "/var/log/apache2/access.log": "Apache访问日志",
    "/var/log/apache2/error.log": "Apache错误日志",
    "/var/log/mysql/error.log": "MySQL错误日志",
    "/var/log/postgresql/postgresql.log": "PostgreSQL日志",
}


def _parse_log_line(line: str) -> LogAnalysisEntry:
    """解析日志行"""
    line_lower = line.lower()
    highlighted = any(kw in line_lower for kw in HIGHLIGHT_KEYWORDS)

    # 检测日志级别
    level = "info"
    if any(kw in line_lower for kw in ["error", "critical", "emergency", "alert"]):
        level = "error"
    elif any(kw in line_lower for kw in ["warning", "warn"]):
        level = "warning"

    # 尝试提取时间戳
    timestamp = None
    ts_match = re.match(r'^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})', line)
    if ts_match:
        timestamp = ts_match.group(1)
    else:
        ts_match = re.match(r'^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})', line)
        if ts_match:
            timestamp = ts_match.group(1)

    return LogAnalysisEntry(line=line, level=level, highlighted=highlighted, timestamp=timestamp)


def _generate_log_read_command(
    log_path: str, page: int = 1, page_size: int = 100,
    filter_text: Optional[str] = None, date_filter: Optional[str] = None,
) -> str:
    """生成读取日志的命令"""
    cmd = f"cat '{log_path}' 2>/dev/null"

    if date_filter:
        cmd = f"grep '{date_filter}' {cmd}"

    if filter_text:
        cmd = f"grep -i '{filter_text}' {cmd}"

    # 分页
    start = (page - 1) * page_size
    cmd = f"{cmd} | tail -n +{start + 1} | head -n {page_size}"

    return cmd


def _generate_journalctl_command(
    page: int = 1, page_size: int = 100,
    unit: Optional[str] = None, filter_text: Optional[str] = None,
    since: Optional[str] = None, until: Optional[str] = None,
) -> str:
    """生成 journalctl 命令"""
    cmd_parts = ["journalctl --no-pager"]

    if unit:
        cmd_parts.append(f"-u {unit}")
    if since:
        cmd_parts.append(f"--since '{since}'")
    if until:
        cmd_parts.append(f"--until '{until}'")
    if filter_text:
        cmd_parts.append(f"--grep '{filter_text}'")

    # 分页
    start = (page - 1) * page_size
    cmd_parts.append(f"--show-cursor")
    cmd = " ".join(cmd_parts)
    cmd = f"{cmd} | tail -n +{start + 1} | head -n {page_size}"

    return cmd


def _generate_list_log_files_command() -> str:
    """生成列出日志文件的命令"""
    return (
        "find /var/log -type f -readable 2>/dev/null | "
        "while read f; do stat -c '%s|%n|%Y' \"$f\" 2>/dev/null; done | head -50"
    )


def _generate_log_file_info_command(log_path: str) -> str:
    """生成获取日志文件信息的命令"""
    return f"stat -c 'size:%s|modified:%Y' '{log_path}' 2>/dev/null || echo 'readable:no'"


async def read_system_log(
    manager: SSHManager,
    log_path: str,
    page: int = 1,
    page_size: int = 100,
    filter_text: Optional[str] = None,
    date_filter: Optional[str] = None,
) -> LogAnalysisOutput:
    """读取系统日志文件"""
    if not manager.is_connected():
        raise ConnectionError("没有活动的 SSH 连接")

    cmd = _generate_log_read_command(log_path, page, page_size, filter_text, date_filter)
    output = await manager.execute_command(cmd)

    entries = []
    for line in output.output.split("\n"):
        line = line.strip()
        if not line or "Log file not found" in line or "No matching entries" in line:
            continue
        entries.append(_parse_log_line(line))

    highlighted_count = sum(1 for e in entries if e.highlighted)

    return LogAnalysisOutput(
        total_count=len(entries),
        highlighted_count=highlighted_count,
        entries=entries,
    )


async def read_journalctl_log(
    manager: SSHManager,
    page: int = 1,
    page_size: int = 100,
    unit: Optional[str] = None,
    filter_text: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> LogAnalysisOutput:
    """读取 journalctl 日志"""
    if not manager.is_connected():
        raise ConnectionError("没有活动的 SSH 连接")

    cmd = _generate_journalctl_command(page, page_size, unit, filter_text, since, until)
    output = await manager.execute_command(cmd)

    entries = []
    for line in output.output.split("\n"):
        line = line.strip()
        if not line or "journalctl not available" in line:
            continue
        entries.append(_parse_log_line(line))

    highlighted_count = sum(1 for e in entries if e.highlighted)

    return LogAnalysisOutput(
        total_count=len(entries),
        highlighted_count=highlighted_count,
        entries=entries,
    )


async def list_log_files(manager: SSHManager) -> List[LogFileInfo]:
    """列出可用的日志文件"""
    if not manager.is_connected():
        raise ConnectionError("没有活动的 SSH 连接")

    cmd = _generate_list_log_files_command()
    output = await manager.execute_command(cmd)

    log_files = []
    for line in output.output.split("\n"):
        parts = line.strip().split("|")
        if len(parts) >= 3:
            try:
                size = int(parts[0])
            except ValueError:
                size = 0
            path = parts[1]
            name = path.rsplit("/", 1)[-1]
            modified = parts[2]
            log_files.append(LogFileInfo(path=path, name=name, size=size, modified=modified, readable=True))

    # 添加常见日志文件
    for path, name in COMMON_LOG_FILES.items():
        if not any(f.path == path for f in log_files):
            log_files.append(LogFileInfo(path=path, name=name, size=0, modified="", readable=False))

    return log_files


async def get_log_file_info(manager: SSHManager, log_path: str) -> LogFileInfo:
    """获取日志文件信息"""
    if not manager.is_connected():
        raise ConnectionError("没有活动的 SSH 连接")

    cmd = _generate_log_file_info_command(log_path)
    output = await manager.execute_command(cmd)
    name = log_path.rsplit("/", 1)[-1]

    if "readable:no" in output.output:
        return LogFileInfo(path=log_path, name=name, size=0, modified="", readable=False)

    size = 0
    modified = ""
    for part in output.output.split("|"):
        if part.startswith("size:"):
            try:
                size = int(part[5:])
            except ValueError:
                pass
        elif part.startswith("modified:"):
            modified = part[9:]

    return LogFileInfo(path=log_path, name=name, size=size, modified=modified, readable=True)
