"""LovelyRes 类型定义 - 从 Rust types.rs 迁移"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


# ==================== SSH 相关类型 ====================


class SSHAccountCredential(BaseModel):
    """SSH账号凭证"""

    username: str
    auth_type: str = "password"  # "password", "key", "certificate"
    encrypted_password: Optional[str] = None
    key_path: Optional[str] = None
    key_passphrase: Optional[str] = None
    certificate_path: Optional[str] = None
    is_default: bool = True
    description: Optional[str] = None


class SSHConnection(BaseModel):
    """SSH连接配置"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "新连接"
    host: str = "localhost"
    port: int = 22
    # 保留单账号字段用于向后兼容
    username: str = "root"
    auth_type: str = "password"
    encrypted_password: Optional[str] = None
    key_path: Optional[str] = None
    key_passphrase: Optional[str] = None
    certificate_path: Optional[str] = None
    # 多账号支持
    accounts: List[SSHAccountCredential] = Field(default_factory=list)
    active_account: Optional[str] = None
    # 其他字段
    is_connected: bool = False
    last_connected: Optional[datetime] = None
    tags: Optional[List[str]] = None

    def migrate_legacy_account(self):
        """从旧的单账号数据迁移到多账号模式"""
        if not self.accounts and self.username:
            account = SSHAccountCredential(
                username=self.username,
                auth_type=self.auth_type,
                encrypted_password=self.encrypted_password,
                key_path=self.key_path,
                key_passphrase=self.key_passphrase,
                certificate_path=self.certificate_path,
                is_default=True,
                description="默认账号（从旧数据迁移）",
            )
            self.accounts.append(account)
            self.active_account = self.username

    def get_default_account(self) -> Optional[SSHAccountCredential]:
        """获取默认账号"""
        for a in self.accounts:
            if a.is_default:
                return a
        return None

    def get_active_account(self) -> Optional[SSHAccountCredential]:
        """获取当前活动账号"""
        if self.active_account:
            for a in self.accounts:
                if a.username == self.active_account:
                    return a
        return self.get_default_account()

    def set_active_account(self, username: str) -> bool:
        """设置活动账号"""
        for a in self.accounts:
            if a.username == username:
                self.active_account = username
                return True
        return False


class SSHCommand(BaseModel):
    """SSH命令配置"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "新命令"
    command: str = "echo 'Hello World'"
    description: str = "示例命令"
    category: str = "其他"
    favorite: bool = False


# ==================== 通用类型 ====================


class AppNotification(BaseModel):
    """应用通知"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    message: str = ""
    notification_type: str = "info"  # "info", "success", "warning", "error"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    read: bool = False


class TerminalSession(BaseModel):
    """终端会话"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    connection_id: str = ""
    created: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True


class FileTransferTask(BaseModel):
    """文件传输任务"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_path: str = ""
    destination_path: str = ""
    transfer_type: str = "upload"  # "upload", "download"
    status: str = "pending"  # "pending", "in_progress", "completed", "failed"
    progress: float = 0.0
    file_size: int = 0
    transferred_size: int = 0
    created: datetime = Field(default_factory=datetime.utcnow)
    completed: Optional[datetime] = None
    error_message: Optional[str] = None


class SystemMonitorData(BaseModel):
    """系统监控数据"""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    disk_usage: float = 0.0
    network_in: int = 0
    network_out: int = 0
    load_average: List[float] = Field(default_factory=list)
    process_count: int = 0


class LogEntry(BaseModel):
    """日志条目"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: str = "info"
    source: str = ""
    message: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ApiResponse(BaseModel):
    """API响应包装器"""

    success: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def ok(cls, data: Any = None) -> "ApiResponse":
        return cls(success=True, data=data)

    @classmethod
    def err(cls, error: str) -> "ApiResponse":
        return cls(success=False, error=error)


class PaginationParams(BaseModel):
    """分页参数"""

    page: int = 1
    page_size: int = 20
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "asc"


class PaginatedResponse(BaseModel):
    """分页响应"""

    items: List[Any] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0

    @classmethod
    def create(
        cls, items: list, total: int, page: int, page_size: int
    ) -> "PaginatedResponse":
        import math

        total_pages = math.ceil(total / page_size) if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class SearchFilter(BaseModel):
    """搜索过滤器"""

    query: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    tags: Optional[List[str]] = None


class AppEvent(BaseModel):
    """应用事件"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    source: str = ""
    data: Any = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BashEnvironmentInfo(BaseModel):
    """Bash 环境信息"""

    bash_version: str = ""
    shell_type: str = "bash"
    ps1: str = ""
    pwd: str = ""
    home: str = ""
    user: str = ""
    hostname: str = ""
    path: str = ""


class CommandCompletion(BaseModel):
    """命令补全建议"""

    completions: List[str] = Field(default_factory=list)
    prefix: str = ""


# ==================== SSH 管理器类型 ====================


class TerminalOutput(BaseModel):
    """终端输出"""

    command: str = ""
    output: str = ""
    exit_code: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def create(
        cls, command: str, output: str, exit_code: Optional[int] = None
    ) -> "TerminalOutput":
        return cls(command=command, output=output, exit_code=exit_code)


class SftpFileInfo(BaseModel):
    """SFTP 文件信息"""

    name: str = ""
    path: str = ""
    file_type: str = "file"  # "directory", "file", "symlink", "other"
    is_dir: bool = False
    size: int = 0
    modified: Optional[str] = None
    permissions: Optional[str] = None


class SftpFileDetails(BaseModel):
    """SFTP 文件详情"""

    name: str = ""
    path: str = ""
    file_type: str = "file"
    size: int = 0
    permissions: str = ""
    owner: Optional[str] = None
    group: Optional[str] = None
    created: Optional[str] = None
    modified: Optional[str] = None
    accessed: Optional[str] = None


class SSHConnectionStatus(BaseModel):
    """SSH 连接状态"""

    connected: bool = False
    host: str = ""
    port: int = 22
    username: str = ""
    last_activity: datetime = Field(default_factory=datetime.utcnow)


class ConnectionInfo(BaseModel):
    """连接信息"""

    host: str = ""
    port: int = 22
    username: str = ""
    auth_method: str = ""


# ==================== 检测结果类型 ====================


class PortScanResult(BaseModel):
    """端口扫描结果"""

    open_ports: List[Dict[str, Any]] = Field(default_factory=list)
    total_open: int = 0
    risk_level: str = "low"
    details: str = ""


class UserAuditResult(BaseModel):
    """用户审计结果"""

    users: List[Dict[str, Any]] = Field(default_factory=list)
    risk_users: List[Dict[str, Any]] = Field(default_factory=list)
    risk_level: str = "low"
    details: str = ""


class BackdoorScanResult(BaseModel):
    """后门检测结果"""

    suspicious_files: List[Dict[str, Any]] = Field(default_factory=list)
    risk_level: str = "low"
    details: str = ""


class ProcessAnalysisResult(BaseModel):
    """进程分析结果"""

    processes: List[Dict[str, Any]] = Field(default_factory=list)
    suspicious_processes: List[Dict[str, Any]] = Field(default_factory=list)
    risk_level: str = "low"
    details: str = ""


class FilePermissionResult(BaseModel):
    """文件权限检测结果"""

    risky_files: List[Dict[str, Any]] = Field(default_factory=list)
    risk_level: str = "low"
    details: str = ""


class SSHAuditResult(BaseModel):
    """SSH 审计结果"""

    config_issues: List[Dict[str, Any]] = Field(default_factory=list)
    risk_level: str = "low"
    details: str = ""


class LogAnalysisResult(BaseModel):
    """日志分析结果"""

    entries: List[Dict[str, Any]] = Field(default_factory=list)
    risk_level: str = "low"
    details: str = ""


class FirewallCheckResult(BaseModel):
    """防火墙检查结果"""

    status: str = ""
    rules: List[Dict[str, Any]] = Field(default_factory=list)
    risk_level: str = "low"
    details: str = ""


class CpuTestResult(BaseModel):
    """CPU 测试结果"""

    cpu_info: str = ""
    cpu_usage: float = 0.0
    details: str = ""


class MemoryTestResult(BaseModel):
    """内存测试结果"""

    total: str = ""
    used: str = ""
    free: str = ""
    usage_percent: float = 0.0
    details: str = ""


class DiskTestResult(BaseModel):
    """磁盘测试结果"""

    disks: List[Dict[str, Any]] = Field(default_factory=list)
    details: str = ""


class NetworkTestResult(BaseModel):
    """网络测试结果"""

    interfaces: List[Dict[str, Any]] = Field(default_factory=list)
    connections: List[Dict[str, Any]] = Field(default_factory=list)
    details: str = ""


class GenericDetectionResult(BaseModel):
    """通用检测结果（基线检测）"""

    title: str = ""
    status: str = "info"  # "pass", "fail", "warn", "info"
    items: List[Dict[str, Any]] = Field(default_factory=list)
    risk_level: str = "low"
    details: str = ""
    suggestions: List[str] = Field(default_factory=list)


# ==================== 日志分析类型 ====================


class LogAnalysisEntry(BaseModel):
    """日志分析条目"""

    line: str = ""
    level: str = "info"
    highlighted: bool = False
    timestamp: Optional[str] = None


class LogAnalysisOutput(BaseModel):
    """日志分析输出"""

    total_count: int = 0
    highlighted_count: int = 0
    entries: List[LogAnalysisEntry] = Field(default_factory=list)
    file_info: Optional[Dict[str, Any]] = None


class LogFileInfo(BaseModel):
    """日志文件信息"""

    path: str = ""
    name: str = ""
    size: int = 0
    modified: str = ""
    readable: bool = True


# ==================== 文件分析类型 ====================


class FileAnalysisResult(BaseModel):
    """文件安全分析结果"""

    path: str = ""
    file_type: str = ""
    size: int = 0
    permissions: str = ""
    owner: str = ""
    group: str = ""
    hash_md5: Optional[str] = None
    hash_sha1: Optional[str] = None
    hash_sha256: Optional[str] = None
    modified: Optional[str] = None
    created: Optional[str] = None
    accessed: Optional[str] = None
    is_suid: bool = False
    is_sgid: bool = False
    is_world_writable: bool = False
    is_hidden: bool = False
    risk_indicators: List[str] = Field(default_factory=list)
    risk_level: str = "low"
    details: str = ""


# ==================== 设备信息类型 ====================


class DeviceInfo(BaseModel):
    """设备信息"""

    device_uuid: str = ""
    device_type: str = ""
    device_name: str = ""
