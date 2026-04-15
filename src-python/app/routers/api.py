"""FastAPI 路由 - 将所有 Tauri 命令映射为 HTTP API

从 Rust lib.rs 中的 Tauri 命令迁移
"""

import os
import tempfile
import time
import json
import asyncio
import urllib.request
import urllib.error
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar

import asyncssh
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.models.types import (
    SSHConnection,
    TerminalOutput,
)
from app.services import detection_manager, file_analysis, log_analysis
from app.services.ssh_connection_manager import SSHConnectionManager
from app.services.ssh_manager import SSHManager
from app.services.settings import (
    AgentSettings,
    AppSettings,
    load_settings,
    read_settings_file,
    save_settings,
    write_settings_file,
)
from app.services.theme_manager import get_theme_settings
from app.services.device_info import get_device_uuid
from app.services.window_manager import WindowManager
from app.utils.crypto import get_rsa_public_key
from app.utils.system_fonts import get_system_fonts

from app.services.agent import (
    AgentOrchestrator,
    AgentRequest,
    get_default_registry,
    get_default_skill_registry,
    HostSummaryBuilder,
    HostSummaryContext,
    PlannerConfig,
    RoleModelConfig,
    UnifiedLLMAdapter,
)

router = APIRouter(prefix="/api/v1", tags=["lovelyres"])

T = TypeVar("T")


async def _wrap_ssh_transport(factory: Callable[[], Awaitable[T]]) -> T:
    """将未连接 SSH、asyncssh 协议错误转为 400，避免未捕获异常变成 500。"""
    try:
        return await factory()
    except ConnectionError as e:
        msg = str(e) or "没有活动的 SSH 连接，请先在应用中连接 SSH 后再使用 SFTP。"
        raise HTTPException(status_code=400, detail=msg) from e
    except asyncssh.Error as e:
        # 含 SFTPError、DisconnectError 等
        raise HTTPException(status_code=400, detail=str(e)) from e


# ==================== 全局状态 ====================

# 这些会在 app 启动时初始化
_ssh_manager: Optional[SSHManager] = None
_ssh_connection_manager: Optional[SSHConnectionManager] = None
_window_manager: Optional[WindowManager] = None
_app_settings: Optional[AppSettings] = None


def init_state():
    """初始化应用状态"""
    global _ssh_manager, _ssh_connection_manager, _window_manager, _app_settings
    _ssh_manager = SSHManager()
    _ssh_connection_manager = SSHConnectionManager()
    _window_manager = WindowManager()
    _app_settings = load_settings()
    print("LovelyRes Python 后端初始化完成")


def get_ssh_manager() -> SSHManager:
    if _ssh_manager is None:
        raise HTTPException(status_code=500, detail="SSH管理器未初始化")
    return _ssh_manager


def get_connection_manager() -> SSHConnectionManager:
    if _ssh_connection_manager is None:
        raise HTTPException(status_code=500, detail="SSH连接管理器未初始化")
    return _ssh_connection_manager


# ==================== 请求模型 ====================


class ConnectDirectRequest(BaseModel):
    host: str
    port: int = 22
    username: str
    password: str


class ConnectWithAuthRequest(BaseModel):
    host: str
    port: int = 22
    username: str
    auth_type: str = "password"
    password: Optional[str] = None
    key_path: Optional[str] = None
    key_passphrase: Optional[str] = None
    certificate_path: Optional[str] = None


class ExecuteCommandRequest(BaseModel):
    command: str
    username: Optional[str] = None


class SftpWriteRequest(BaseModel):
    path: str
    content: str


class SftpCompressRequest(BaseModel):
    source_path: str
    target_path: str
    format: str = "tar.gz"


class SftpExtractRequest(BaseModel):
    archive_path: str
    target_dir: str
    overwrite: bool = True


class SftpUploadRequest(BaseModel):
    local_path: str
    remote_path: str


class SftpDownloadRequest(BaseModel):
    remote_path: str
    local_path: str


class SftpChmodRequest(BaseModel):
    path: str
    mode: int


class SaveTempFileRequest(BaseModel):
    file_name: str
    data: str  # base64 encoded


class DockerActionRequest(BaseModel):
    container_id: str
    action: str


class DockerLogsRequest(BaseModel):
    container_id: str
    options: Optional[DockerLogsOptions] = None


class DockerExecRequest(BaseModel):
    container_id: str
    command: str
    shell: str = "sh"


class DockerWriteFileRequest(BaseModel):
    container_id: str
    path: str
    content: str


class DockerCopyRequest(BaseModel):
    container_id: str
    direction: str
    source: str
    target: str


class CreateTerminalSessionRequest(BaseModel):
    terminal_id: str
    cols: int = 80
    rows: int = 24


class SendTerminalInputRequest(BaseModel):
    terminal_id: str
    data: str


class SetThemeRequest(BaseModel):
    theme: str


class SaveSettingsRequest(BaseModel):
    settings: Dict[str, Any]


class WriteSettingsFileRequest(BaseModel):
    content: str


class EncryptPasswordRequest(BaseModel):
    password: str


class DecryptPasswordRequest(BaseModel):
    encrypted_password: str


class AIProxyRequest(BaseModel):
    url: str
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = 60


class ReadSystemLogRequest(BaseModel):
    log_path: str
    page: int = 1
    page_size: int = 100
    filter: Optional[str] = None
    date_filter: Optional[str] = None


class ReadJournalctlLogRequest(BaseModel):
    page: int = 1
    page_size: int = 100
    unit: Optional[str] = None
    filter: Optional[str] = None
    since: Optional[str] = None
    until: Optional[str] = None


class FileAnalysisRequest(BaseModel):
    path: str


class DialogFilterRequest(BaseModel):
    name: Optional[str] = None
    extensions: List[str] = Field(default_factory=list)


class OpenDialogRequest(BaseModel):
    multiple: bool = False
    directory: bool = False
    filters: List[DialogFilterRequest] = Field(default_factory=list)
    default_path: Optional[str] = None


class SaveDialogRequest(BaseModel):
    filters: List[DialogFilterRequest] = Field(default_factory=list)
    default_path: Optional[str] = None


class AgentRunRequest(BaseModel):
    """Agent 运行请求"""

    task: str
    skills: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    max_steps: int = 10


def _run_native_dialog(kind: str, options: Dict[str, Any]) -> Any:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise RuntimeError("当前环境不支持本机文件对话框") from exc

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except Exception:
        pass
    root.update()

    filters = options.get("filters") or []
    filetypes = []
    for item in filters:
        name = item.get("name") or "支持的文件"
        extensions = item.get("extensions") or []
        patterns = []
        for ext in extensions:
            if ext == "*":
                patterns.append("*.*")
            else:
                patterns.append(ext if ext.startswith("*.") else f"*.{ext.lstrip('.')}")
        if patterns:
            filetypes.append((name, " ".join(patterns)))

    if not filetypes:
        filetypes = [("所有文件", "*.*")]

    initialdir = None
    initialfile = None
    default_path = options.get("default_path")
    if default_path:
        normalized = os.path.normpath(default_path)
        if os.path.isdir(normalized):
            initialdir = normalized
        else:
            initialdir = os.path.dirname(normalized) or None
            initialfile = os.path.basename(normalized) or None

    dialog_kwargs: Dict[str, Any] = {"parent": root}
    if initialdir:
        dialog_kwargs["initialdir"] = initialdir
    if initialfile:
        dialog_kwargs["initialfile"] = initialfile
    if kind != "open_directory":
        dialog_kwargs["filetypes"] = filetypes

    try:
        if kind == "open_directory":
            result = filedialog.askdirectory(**dialog_kwargs)
        elif kind == "open_files":
            result = filedialog.askopenfilenames(**dialog_kwargs)
        elif kind == "open_file":
            result = filedialog.askopenfilename(**dialog_kwargs)
        elif kind == "save_file":
            result = filedialog.asksaveasfilename(**dialog_kwargs)
        else:
            raise RuntimeError("不支持的对话框类型")
    finally:
        root.destroy()

    if kind == "open_files":
        return list(result) if result else []
    return result or None


# ==================== 窗口控制 ====================


@router.post("/window/minimize")
async def minimize_window():
    """最小化窗口 - 通过事件通知前端"""
    return {"event": "window-minimize"}


@router.post("/window/toggle-maximize")
async def toggle_maximize():
    """切换最大化 - 通过事件通知前端"""
    return {"event": "window-toggle-maximize"}


@router.post("/window/close")
async def close_window():
    """关闭窗口 - 通过事件通知前端"""
    return {"event": "window-close"}


@router.post("/window/open-devtools")
async def open_devtools():
    """打开开发者工具 - 通过事件通知前端"""
    return {"event": "window-open-devtools"}


@router.post("/dialog/open")
async def open_dialog(req: OpenDialogRequest):
    """打开本机文件/目录选择对话框"""
    kind = (
        "open_directory"
        if req.directory
        else "open_files"
        if req.multiple
        else "open_file"
    )
    try:
        path = await asyncio.to_thread(
            _run_native_dialog,
            kind,
            req.model_dump(),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"打开文件对话框失败: {exc}"
        ) from exc

    return {"path": path if path else None}


@router.post("/dialog/save")
async def save_dialog(req: SaveDialogRequest):
    """打开本机保存文件对话框"""
    try:
        path = await asyncio.to_thread(
            _run_native_dialog,
            "save_file",
            req.model_dump(),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"打开保存对话框失败: {exc}"
        ) from exc

    return {"path": path if path else None}


# ==================== 主题管理 ====================


@router.get("/theme/settings")
async def get_theme():
    """获取主题设置"""
    current_theme = _app_settings.theme if _app_settings else "light"
    return get_theme_settings(current_theme)


@router.post("/theme/set")
async def set_current_theme(req: SetThemeRequest):
    """设置当前主题"""
    global _app_settings
    if _app_settings:
        _app_settings.theme = req.theme
        save_settings(_app_settings)
    return {"event": "theme-changed", "theme": req.theme}


# ==================== 设置管理 ====================


@router.get("/settings")
async def get_app_settings():
    """获取应用设置"""
    global _app_settings
    if _app_settings is None:
        _app_settings = load_settings()
    return _app_settings.model_dump()


@router.post("/settings/save")
async def save_app_settings(req: SaveSettingsRequest):
    """保存应用设置"""
    global _app_settings
    try:
        _app_settings = AppSettings.model_validate(req.settings)
        save_settings(_app_settings)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/settings/file")
async def read_settings():
    """读取设置文件"""
    return {"content": read_settings_file()}


@router.post("/settings/file/write")
async def write_settings(req: WriteSettingsFileRequest):
    """写入设置文件"""
    write_settings_file(req.content)
    return {"success": True}


@router.get("/system/fonts")
async def get_fonts():
    """获取系统字体列表"""
    return {"fonts": get_system_fonts()}


# ==================== SSH 连接管理 ====================


@router.get("/ssh/connections")
async def load_ssh_connections():
    """加载 SSH 连接列表"""
    manager = get_connection_manager()
    connections = manager.load_connections()
    return [c.model_dump(mode="json") for c in connections]


@router.post("/ssh/connections/save")
async def save_ssh_connections(connections: List[SSHConnection]):
    """保存 SSH 连接列表"""
    manager = get_connection_manager()
    manager.save_connections(connections)
    return {"success": True}


@router.post("/ssh/encrypt-password")
async def encrypt_password(req: EncryptPasswordRequest):
    """加密密码"""
    manager = get_connection_manager()
    return {"encrypted": manager.encrypt_password(req.password)}


@router.post("/ssh/decrypt-password")
async def decrypt_password(req: DecryptPasswordRequest):
    """解密密码"""
    manager = get_connection_manager()
    return {"decrypted": manager.decrypt_password(req.encrypted_password)}


@router.post("/ssh/connect")
async def ssh_connect_with_auth(req: ConnectWithAuthRequest):
    """SSH 连接（支持密码/密钥/证书）"""
    ssh = get_ssh_manager()
    try:
        result = await ssh.connect(
            host=req.host,
            port=req.port,
            username=req.username,
            password=req.password,
            private_key=req.key_path,
            key_passphrase=req.key_passphrase,
        )
        return {"message": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ssh/test-connection")
async def ssh_test_connection(req: ConnectWithAuthRequest):
    """测试 SSH 连接"""
    ssh = get_ssh_manager()
    try:
        await ssh.connect(
            host=req.host,
            port=req.port,
            username=req.username,
            password=req.password,
            private_key=req.key_path,
            key_passphrase=req.key_passphrase,
        )
        await ssh.disconnect()
        return {"success": True}
    except Exception:
        return {"success": False}


@router.post("/ssh/execute-command")
async def ssh_execute_command(req: ExecuteCommandRequest):
    """执行 SSH 命令"""
    ssh = get_ssh_manager()
    result = await ssh.execute_command(req.command)
    return result.model_dump(mode="json")


@router.post("/ssh/disconnect")
async def ssh_disconnect():
    """断开 SSH 连接"""
    ssh = get_ssh_manager()
    await ssh.disconnect()
    return {"success": True}


# ==================== SSH/SFTP 直接命令 ====================


@router.post("/ssh/connect-direct")
async def ssh_connect_direct(req: ConnectDirectRequest):
    """直接 SSH 连接"""
    ssh = get_ssh_manager()
    try:
        await ssh.connect(
            host=req.host,
            port=req.port,
            username=req.username,
            password=req.password,
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ssh/disconnect-direct")
async def ssh_disconnect_direct():
    """直接断开连接"""
    ssh = get_ssh_manager()
    await ssh.disconnect()
    return {"success": True}


@router.post("/ssh/execute-command-direct")
async def ssh_execute_command_direct(req: ExecuteCommandRequest):
    """直接执行命令"""
    ssh = get_ssh_manager()
    result = await ssh.execute_dashboard_command_as_user(req.command, req.username)
    return result.model_dump(mode="json")


@router.post("/ssh/execute-dashboard-command")
async def ssh_execute_dashboard_command(req: ExecuteCommandRequest):
    """仪表盘命令执行"""
    ssh = get_ssh_manager()
    result = await ssh.execute_dashboard_command(req.command)
    return result.model_dump(mode="json")


@router.post("/ssh/execute-emergency-command")
async def ssh_execute_emergency_command(req: ExecuteCommandRequest):
    """应急响应命令执行"""
    ssh = get_ssh_manager()
    if req.username:
        result = await ssh.execute_dashboard_command_as_user(req.command, req.username)
    else:
        result = await ssh.execute_dashboard_command(req.command)
    return result.model_dump(mode="json")


@router.post("/ssh/execute-detection-command")
async def execute_detection_command(req: ExecuteCommandRequest):
    """执行 AI 生成的检测命令"""
    ssh = get_ssh_manager()
    result = await ssh.execute_dashboard_command(req.command)
    return result.model_dump(mode="json")


@router.get("/ssh/connection-status")
async def ssh_get_connection_status():
    """获取连接状态"""
    ssh = get_ssh_manager()
    status = await ssh.get_connection_status()
    return status.model_dump(mode="json") if status else None


@router.post("/ssh/test-performance")
async def test_ssh_performance():
    """测试 SSH 连接质量"""
    ssh = get_ssh_manager()
    test_commands = [
        ("echo test", "基础响应测试"),
        ("pwd", "目录查询测试"),
        ("date", "系统时间测试"),
        ("whoami", "用户查询测试"),
    ]

    results = ["=== 直接命令执行性能测试 ==="]
    for cmd, desc in test_commands:
        start = time.time()
        try:
            await ssh.execute_command(cmd)
            duration = time.time() - start
            results.append(f"{desc}: {duration:.3f}s")
        except Exception as e:
            results.append(f"{desc}: 失败 - {e}")

    results.append("\n=== 性能分析建议 ===")
    results.append("如果直接命令执行很快，但交互式终端很慢，问题可能在于:")
    results.append("1. Shell初始化配置(.bashrc, .profile)")
    results.append("2. 复杂的命令提示符(PS1)")
    results.append("3. PTY配置问题")
    results.append("4. 环境变量处理")

    return {"result": "\n".join(results)}


@router.post("/ssh/diagnose-shell-performance")
async def diagnose_shell_performance():
    """检测 Shell 配置可能导致的性能问题"""
    ssh = get_ssh_manager()
    results = ["=== Shell性能诊断 ==="]

    tests = [
        ("echo $SHELL", "Shell类型"),
        ("wc -l ~/.bashrc 2>/dev/null || echo 'no .bashrc'", ".bashrc行数"),
        ('echo "PS1长度: ${#PS1}"', "命令提示符"),
        ("true", "简单命令(true)"),
    ]

    for cmd, desc in tests:
        start = time.time()
        try:
            output = await ssh.execute_command(cmd)
            duration = time.time() - start
            results.append(f"{desc}: {output.output.strip()} (耗时: {duration:.3f}s)")
        except Exception as e:
            results.append(f"{desc}失败: {e}")

    return {"result": "\n".join(results)}


@router.get("/ssh/detect-system-type")
async def detect_system_type():
    """检测系统类型"""
    ssh = get_ssh_manager()
    if not ssh.is_connected():
        raise HTTPException(status_code=400, detail="没有活动的 SSH 连接")

    # 读取 os-release
    os_release_cmd = "cat /etc/os-release 2>/dev/null || cat /etc/lsb-release 2>/dev/null || echo 'ID=generic'"
    os_release_output = await ssh.execute_dashboard_command(os_release_cmd)
    os_release_content = os_release_output.output

    # 检测包管理器
    pkg_mgr_cmd = "which apt 2>/dev/null && echo 'apt' || which yum 2>/dev/null && echo 'yum' || which dnf 2>/dev/null && echo 'dnf' || which pacman 2>/dev/null && echo 'pacman' || which zypper 2>/dev/null && echo 'zypper' || which apk 2>/dev/null && echo 'apk' || echo 'unknown'"
    pkg_mgr_output = await ssh.execute_dashboard_command(pkg_mgr_cmd)
    package_manager = pkg_mgr_output.output.strip().split("\n")[-1].strip()

    # 检测 init 系统
    init_output = await ssh.execute_dashboard_command("ps -p 1 -o comm= 2>/dev/null")
    init_str = init_output.output.strip().lower()
    if "systemd" in init_str:
        init_system = "systemd"
    elif "init" in init_str:
        init_system = "sysvinit"
    elif "upstart" in init_str:
        init_system = "upstart"
    elif "openrc" in init_str:
        init_system = "openrc"
    else:
        init_system = "unknown"

    # 解析 os-release
    id_val = "generic"
    id_like = ""
    name = "Linux"
    version = ""
    pretty_name = "Generic Linux"

    for line in os_release_content.split("\n"):
        line = line.strip()
        if line.startswith("ID=") and not line.startswith("ID_LIKE="):
            id_val = line[3:].strip('"').strip("'").lower()
        elif line.startswith("ID_LIKE="):
            id_like = line[8:].strip('"').strip("'").lower()
        elif line.startswith("NAME="):
            name = line[5:].strip('"').strip("'")
        elif line.startswith("VERSION_ID="):
            version = line[11:].strip('"').strip("'")
        elif line.startswith("PRETTY_NAME="):
            pretty_name = line[12:].strip('"').strip("'")

    # 识别系统类型
    system_type = id_val
    if id_val in (
        "kylin",
        "uos",
        "uniontech",
        "deepin",
        "openeuler",
        "anolis",
        "ubuntu",
        "debian",
        "centos",
        "rhel",
        "fedora",
        "arch",
        "alpine",
    ):
        system_type = id_val
    elif id_val in ("opensuse", "suse"):
        system_type = "opensuse"
    elif id_like:
        if "ubuntu" in id_like:
            system_type = "ubuntu"
        elif "debian" in id_like:
            system_type = "debian"
        elif "rhel" in id_like or "fedora" in id_like:
            combined = f"{id_val} {id_like} {name} {pretty_name}".lower()
            if "centos" in combined:
                system_type = "centos"
            elif "fedora" in combined:
                system_type = "fedora"
            else:
                system_type = "rhel"
        elif "arch" in id_like:
            system_type = "arch"
        elif "suse" in id_like:
            system_type = "opensuse"
        else:
            system_type = "generic"
    else:
        system_type = "generic"

    return {
        "type": system_type,
        "name": name,
        "version": version,
        "prettyName": pretty_name,
        "packageManager": package_manager,
        "initSystem": init_system,
    }


# ==================== SFTP 文件操作 ====================


@router.post("/sftp/list-files")
async def sftp_list_files(path: str):
    """列出文件/目录"""

    async def _go():
        ssh = get_ssh_manager()
        return await ssh.list_sftp_files(path)

    files = await _wrap_ssh_transport(_go)
    return [f.model_dump(mode="json") for f in files]


@router.post("/sftp/read-file")
async def sftp_read_file(path: str, max_bytes: Optional[int] = None):
    """读取文件"""

    async def _go():
        ssh = get_ssh_manager()
        return await ssh.read_sftp_file(path)

    content = await _wrap_ssh_transport(_go)
    text = content.decode("utf-8", errors="replace")
    if max_bytes and len(text) > max_bytes:
        text = text[:max_bytes]
    return {"content": text}


@router.post("/sftp/write-file")
async def sftp_write_file(req: SftpWriteRequest):
    """写入文件"""

    async def _go():
        ssh = get_ssh_manager()
        await ssh.write_sftp_file(req.path, req.content.encode("utf-8"))

    await _wrap_ssh_transport(_go)
    return {"success": True}


@router.post("/sftp/upload")
async def sftp_upload(req: SftpUploadRequest):
    """上传文件"""

    async def _go():
        ssh = get_ssh_manager()
        await ssh.upload_file(req.local_path, req.remote_path)

    await _wrap_ssh_transport(_go)
    return {"success": True}


@router.post("/sftp/download")
async def sftp_download(req: SftpDownloadRequest):
    """下载文件"""

    async def _go():
        ssh = get_ssh_manager()
        await ssh.download_file(req.remote_path, req.local_path)

    await _wrap_ssh_transport(_go)
    return {"success": True}


@router.post("/sftp/create-directory")
async def sftp_create_directory(remote_path: str):
    """创建目录"""

    async def _go():
        ssh = get_ssh_manager()
        await ssh.create_directory(remote_path)

    await _wrap_ssh_transport(_go)
    return {"success": True}


@router.post("/sftp/compress")
async def sftp_compress(req: SftpCompressRequest):
    """压缩文件"""

    async def _go():
        ssh = get_ssh_manager()
        await ssh.compress_file(req.source_path, req.target_path, req.format)

    await _wrap_ssh_transport(_go)
    return {"success": True}


@router.post("/sftp/extract")
async def sftp_extract(req: SftpExtractRequest):
    """解压文件"""

    async def _go():
        ssh = get_ssh_manager()
        await ssh.extract_file(req.archive_path, req.target_dir)

    await _wrap_ssh_transport(_go)
    return {"success": True}


@router.post("/sftp/chmod")
async def sftp_chmod(req: SftpChmodRequest):
    """修改权限"""

    async def _go():
        ssh = get_ssh_manager()
        await ssh.chmod_sftp(req.path, req.mode)

    await _wrap_ssh_transport(_go)
    return {"success": True}


@router.post("/sftp/get-file-details")
async def sftp_get_file_details(path: str):
    """获取文件详情"""

    async def _go():
        ssh = get_ssh_manager()
        return await ssh.get_file_details(path)

    details = await _wrap_ssh_transport(_go)
    return details.model_dump(mode="json")


@router.post("/sftp/save-temp-file")
async def save_temp_file(req: SaveTempFileRequest):
    """保存临时文件"""
    import base64

    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, req.file_name)
    data = base64.b64decode(req.data)
    with open(temp_path, "wb") as f:
        f.write(data)
    return {"path": temp_path}


# ==================== 文件安全分析 ====================


@router.post("/file-analysis")
async def sftp_file_analysis_endpoint(req: FileAnalysisRequest):
    """文件安全分析"""

    async def _go():
        ssh = get_ssh_manager()
        return await file_analysis.sftp_file_analysis(ssh, req.path)

    result = await _wrap_ssh_transport(_go)
    return result.model_dump()


@router.post("/file-analysis/independent")
async def sftp_file_analysis_independent_endpoint(req: FileAnalysisRequest):
    """独立文件分析"""

    async def _go():
        ssh = get_ssh_manager()
        return await file_analysis.sftp_file_analysis_independent(ssh, req.path)

    result = await _wrap_ssh_transport(_go)
    return result.model_dump()


# ==================== Bash 环境 & 命令补全 ====================


@router.get("/bash/environment-info")
async def get_bash_environment_info():
    """获取 Bash 环境信息"""
    ssh = get_ssh_manager()
    result = await ssh.get_bash_environment_info()
    return result.model_dump()


@router.post("/command/completion")
async def get_command_completion(input: str):
    """获取命令补全建议"""
    ssh = get_ssh_manager()
    result = await ssh.get_command_completion(input)
    return result.model_dump()


# ==================== 安全检测命令 ====================


@router.post("/detect/port-scan")
async def detect_port_scan():
    return (await detection_manager.detect_port_scan(get_ssh_manager())).model_dump()


@router.post("/detect/user-audit")
async def detect_user_audit():
    return (await detection_manager.detect_user_audit(get_ssh_manager())).model_dump()


@router.post("/detect/backdoor")
async def detect_backdoor():
    return (await detection_manager.detect_backdoor(get_ssh_manager())).model_dump()


@router.post("/detect/process-analysis")
async def detect_process_analysis():
    return (
        await detection_manager.detect_process_analysis(get_ssh_manager())
    ).model_dump()


@router.post("/detect/file-permission")
async def detect_file_permission():
    return (
        await detection_manager.detect_file_permission(get_ssh_manager())
    ).model_dump()


@router.post("/detect/ssh-audit")
async def detect_ssh_audit():
    return (await detection_manager.detect_ssh_audit(get_ssh_manager())).model_dump()


@router.post("/detect/log-analysis")
async def detect_log_analysis():
    return (await detection_manager.detect_log_analysis(get_ssh_manager())).model_dump()


@router.post("/detect/firewall-check")
async def detect_firewall_check():
    return (
        await detection_manager.detect_firewall_check(get_ssh_manager())
    ).model_dump()


@router.post("/detect/cpu-test")
async def detect_cpu_test():
    return (await detection_manager.detect_cpu_test(get_ssh_manager())).model_dump()


@router.post("/detect/memory-test")
async def detect_memory_test():
    return (await detection_manager.detect_memory_test(get_ssh_manager())).model_dump()


@router.post("/detect/disk-test")
async def detect_disk_test():
    return (await detection_manager.detect_disk_test(get_ssh_manager())).model_dump()


@router.post("/detect/network-test")
async def detect_network_test():
    return (await detection_manager.detect_network_test(get_ssh_manager())).model_dump()


# ==================== 基线检测命令 ====================


@router.post("/detect/password-policy")
async def detect_password_policy():
    return (
        await detection_manager.detect_password_policy(get_ssh_manager())
    ).model_dump()


@router.post("/detect/sudo-config")
async def detect_sudo_config():
    return (await detection_manager.detect_sudo_config(get_ssh_manager())).model_dump()


@router.post("/detect/pam-config")
async def detect_pam_config():
    return (await detection_manager.detect_pam_config(get_ssh_manager())).model_dump()


@router.post("/detect/account-lockout")
async def detect_account_lockout():
    return (
        await detection_manager.detect_account_lockout(get_ssh_manager())
    ).model_dump()


@router.post("/detect/selinux-status")
async def detect_selinux_status():
    return (
        await detection_manager.detect_selinux_status(get_ssh_manager())
    ).model_dump()


@router.post("/detect/kernel-params")
async def detect_kernel_params():
    return (
        await detection_manager.detect_kernel_params(get_ssh_manager())
    ).model_dump()


@router.post("/detect/system-updates")
async def detect_system_updates():
    return (
        await detection_manager.detect_system_updates(get_ssh_manager())
    ).model_dump()


@router.post("/detect/unnecessary-services")
async def detect_unnecessary_services():
    return (
        await detection_manager.detect_unnecessary_services(get_ssh_manager())
    ).model_dump()


@router.post("/detect/auto-start-services")
async def detect_auto_start_services():
    return (
        await detection_manager.detect_auto_start_services(get_ssh_manager())
    ).model_dump()


@router.post("/detect/audit-config")
async def detect_audit_config():
    return (await detection_manager.detect_audit_config(get_ssh_manager())).model_dump()


@router.post("/detect/history-audit")
async def detect_history_audit():
    return (
        await detection_manager.detect_history_audit(get_ssh_manager())
    ).model_dump()


@router.post("/detect/ntp-config")
async def detect_ntp_config():
    return (await detection_manager.detect_ntp_config(get_ssh_manager())).model_dump()


@router.post("/detect/dns-config")
async def detect_dns_config():
    return (await detection_manager.detect_dns_config(get_ssh_manager())).model_dump()


# ==================== SSH 终端管理 ====================


@router.post("/ssh/terminal/create")
async def ssh_create_terminal_session(req: CreateTerminalSessionRequest):
    """创建终端会话"""
    ssh = get_ssh_manager()
    try:
        result = await ssh.create_terminal_session(req.terminal_id, req.cols, req.rows)
        return {"terminal_id": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ssh/terminal/close")
async def ssh_close_terminal_session(terminal_id: str):
    """关闭终端会话"""
    ssh = get_ssh_manager()
    await ssh.close_terminal_session(terminal_id)
    return {"success": True}


@router.post("/ssh/terminal/close-all")
async def ssh_close_all_terminal_sessions():
    """关闭所有终端会话"""
    ssh = get_ssh_manager()
    await ssh.close_all_terminal_sessions()
    return {"success": True}


@router.post("/ssh/terminal/send-input")
async def ssh_send_input(req: SendTerminalInputRequest):
    """向终端发送输入"""
    ssh = get_ssh_manager()
    await ssh.send_terminal_input(req.terminal_id, req.data.encode("utf-8"))
    return {"success": True}


@router.post("/ssh/terminal/get-completion")
async def ssh_get_completion(input: str):
    """获取终端自动补全"""
    ssh = get_ssh_manager()
    result = await ssh.get_command_completion(input)
    return result.model_dump()


# ==================== 日志分析 ====================


@router.post("/log/read-system")
async def read_system_log(req: ReadSystemLogRequest):
    """读取系统日志文件"""
    ssh = get_ssh_manager()
    result = await log_analysis.read_system_log(
        ssh, req.log_path, req.page, req.page_size, req.filter, req.date_filter
    )
    return result.model_dump()


@router.post("/log/read-journalctl")
async def read_journalctl_log(req: ReadJournalctlLogRequest):
    """读取 journalctl 日志"""
    ssh = get_ssh_manager()
    result = await log_analysis.read_journalctl_log(
        ssh, req.page, req.page_size, req.unit, req.filter, req.since, req.until
    )
    return result.model_dump()


@router.get("/log/list-files")
async def list_log_files():
    """列出可用的日志文件"""
    ssh = get_ssh_manager()
    files = await log_analysis.list_log_files(ssh)
    return [f.model_dump() for f in files]


@router.post("/log/file-info")
async def get_log_file_info(log_path: str):
    """获取日志文件信息"""
    ssh = get_ssh_manager()
    info = await log_analysis.get_log_file_info(ssh, log_path)
    return info.model_dump()


def _do_ai_proxy_post(
    url: str, headers: Dict[str, str], body: Dict[str, Any], timeout_seconds: int
) -> Dict[str, Any]:
    payload = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url=url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in headers.items():
        if not k or not isinstance(k, str):
            continue
        # 仅透传基础文本头，避免注入异常头
        if "\n" in k or "\r" in k:
            continue
        req.add_header(k, str(v))

    with urllib.request.urlopen(req, timeout=max(5, timeout_seconds)) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)


@router.post("/ai/chat-proxy")
async def ai_chat_proxy(req: AIProxyRequest):
    """AI 请求后端代理，规避浏览器 CORS 限制。"""
    try:
        data = await asyncio.to_thread(
            _do_ai_proxy_post,
            req.url,
            req.headers,
            req.body,
            req.timeout_seconds,
        )
        return {"ok": True, "data": data}
    except urllib.error.HTTPError as e:
        try:
            err_text = e.read().decode("utf-8", errors="replace")
        except Exception:
            err_text = str(e)
        raise HTTPException(
            status_code=502, detail=f"上游 AI API 错误: {e.code} - {err_text}"
        ) from e
    except urllib.error.URLError as e:
        raise HTTPException(
            status_code=502, detail=f"无法连接上游 AI API: {e.reason}"
        ) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 代理请求失败: {e}") from e


# ==================== 加密 & 设备信息 ====================


@router.get("/crypto/rsa-public-key")
async def get_rsa_key():
    """获取 RSA 公钥"""
    return {"public_key": get_rsa_public_key()}


@router.get("/device/uuid")
async def get_device_uuid_endpoint():
    """获取设备 UUID"""
    info = get_device_uuid()
    return info.model_dump()


# ==================== Agent API ====================


def _get_agent_config() -> Optional[AgentSettings]:
    """读取 settings.agent 配置（只读，不做默认合并）

    注意:
      - 返回 None 表示 settings 未加载
      - agent.enabled=False 时 /agent/run 会提前返回，不抛异常
    """
    global _app_settings
    if _app_settings is None:
        return None
    return _app_settings.agent


@router.post("/agent/run")
async def agent_run(req: AgentRunRequest):
    """运行 Agent 任务"""
    global _app_settings
    agent_config = _get_agent_config()

    if agent_config is None or not agent_config.enabled:
        return {
            "id": "",
            "request_id": getattr(req, "id", ""),
            "task": req.task,
            "status": "failed",
            "skill_name": None,
            "plan": None,
            "traces": [],
            "final": {
                "summary": "Agent 功能已禁用",
                "evidence": [],
                "risks": [],
                "recommendations": [],
                "commands": [],
                "next_actions": [],
            },
            "skill_results": [],
            "raw_summary": "Agent 功能已禁用",
            "structured_output": {},
            "total_duration_ms": 0,
            "created_at": "",
        }

    ssh = get_ssh_manager()

    context = dict(req.context)
    context["ssh_manager"] = ssh

    planner_config = PlannerConfig(
        enable_llm_planner=agent_config.planner.enable_llm_planner,
        max_skills_per_task=agent_config.planner.max_skills_per_task,
    )

    runtime_registry = None
    try:
        from app.services.agent.tool_registry import get_runtime_registry

        settings = _app_settings if _app_settings is not None else load_settings()
        runtime_registry = await get_runtime_registry(settings)
    except Exception:
        pass

    orchestrator = AgentOrchestrator(
        planner_config=planner_config,
        tool_registry=runtime_registry,
    )

    agent_request = AgentRequest(
        task=req.task,
        skills=req.skills,
        context=context,
        max_steps=req.max_steps,
    )

    report = await orchestrator.run(agent_request)

    return {
        "id": report.id,
        "request_id": report.request_id,
        "task": report.task,
        "status": report.status,
        "skill_name": report.skill_name,
        "plan": report.plan,
        "traces": report.traces,
        "final": report.final,
        "skill_results": [
            {
                "skill_name": sr.skill_name,
                "summary": sr.summary,
                "risk_level": sr.risk_level,
                "recommendations": sr.recommendations,
                "findings_count": len(sr.findings),
            }
            for sr in report.skill_results
        ],
        "raw_summary": report.raw_summary,
        "structured_output": report.structured_output,
        "total_duration_ms": report.total_duration_ms,
        "created_at": report.created_at.isoformat(),
    }


@router.get("/agent/context")
async def agent_get_context():
    """获取 Agent 上下文信息"""
    ssh = get_ssh_manager()

    if not ssh.is_connected():
        return {
            "connected": False,
            "host_info": None,
            "summary": None,
        }

    from app.services.agent.schemas import HostInfo

    try:
        result = await ssh.execute_command("hostname")
        hostname = result.output.strip() if result.exit_code == 0 else "unknown"

        result = await ssh.execute_command("uname -a")
        uname_output = result.output.strip() if result.exit_code == 0 else ""

        result = await ssh.execute_command("free -h")
        memory_output = result.output.strip() if result.exit_code == 0 else ""

        result = await ssh.execute_command("df -h")
        disk_output = result.output.strip() if result.exit_code == 0 else ""

        host_info = HostInfo(
            hostname=hostname,
            os=uname_output,
            memory_total=memory_output.split("\n")[1] if memory_output else "N/A",
            disk_total=disk_output.split("\n")[1] if disk_output else "N/A",
        )

        host_context = HostSummaryContext(
            host_info=host_info,
            recent_commands=[],
            suspicious_processes=[],
            open_ports=[],
            risk_level="unknown",
            recommendations=[],
        )

        summary = HostSummaryBuilder.build_summary(host_context)

        return {
            "connected": True,
            "host_info": host_info.model_dump(),
            "summary": summary,
        }

    except Exception as e:
        return {
            "connected": True,
            "host_info": None,
            "summary": None,
            "error": str(e),
        }


@router.get("/agent/tools")
async def agent_get_tools():
    """获取可用工具列表 (内置 + MCP)"""
    registry = get_default_registry()
    tools = registry.list_tools()

    internal_tools = [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "source": "internal",
            "risk_level": "low",
            "enabled": getattr(t, "enabled", True),
        }
        for t in tools
    ]

    mcp_tools = []
    try:
        from app.services.agent.mcp import get_enabled_mcp_tools

        mcp_tools = get_enabled_mcp_tools()
    except Exception:
        pass

    all_tools = internal_tools + mcp_tools
    return {
        "tools": all_tools,
        "count": len(all_tools),
        "internal_count": len(internal_tools),
        "mcp_count": len(mcp_tools),
    }


@router.get("/agent/skills")
async def agent_get_skills():
    """获取可用 Skills 列表"""
    registry = get_default_skill_registry()
    skills = registry.list_skills()

    return {
        "skills": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "category": s.category,
                "step_count": len(s.steps),
            }
            for s in skills
        ],
        "count": len(skills),
    }
