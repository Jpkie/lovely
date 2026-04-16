"""设置管理模块 - 从 Rust settings.rs 迁移"""

import json
import os
import platform
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


# ==================== 设置模型 ====================


class NotificationSettings(BaseModel):
    enabled: bool = True
    connection_status: bool = True
    command_completion: bool = False
    error_alerts: bool = True


class SecuritySettings(BaseModel):
    save_passwords: bool = False
    session_timeout: int = 86400000  # 24小时
    require_confirmation: bool = False


class UISettings(BaseModel):
    sidebar_width: int = 280
    show_status_bar: bool = False if platform.system() == "Windows" else True
    compact_mode: bool = False
    animations_enabled: bool = True


class SSHSettings(BaseModel):
    keep_alive_interval: int = 30000
    connection_timeout: int = 0
    max_retries: int = 3


class AgentModelSettings(BaseModel):
    """Agent 模型配置"""

    provider: str = "openai"
    model_name: str = "gpt-4"
    api_key: Optional[str] = None
    base_url: str = "https://api.openai.com/v1"
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60
    fallback_model: Optional[str] = None


class AgentPlannerSettings(BaseModel):
    """Agent Planner 配置"""

    enable_llm_planner: bool = False
    max_skills_per_task: int = 3


class AgentSettings(BaseModel):
    """Agent 设置"""

    enabled: bool = True
    skills_enabled: bool = True
    mcp_enabled: bool = False
    multi_model_enabled: bool = False
    planner: AgentPlannerSettings = Field(default_factory=AgentPlannerSettings)
    router_model: AgentModelSettings = Field(
        default_factory=lambda: AgentModelSettings(model_name="gpt-4")
    )
    planner_model: AgentModelSettings = Field(default_factory=AgentModelSettings)
    analyst_model: AgentModelSettings = Field(
        default_factory=lambda: AgentModelSettings(model_name="gpt-3.5-turbo")
    )
    judge_model: AgentModelSettings = Field(
        default_factory=lambda: AgentModelSettings(model_name="gpt-4")
    )
    executor_model: AgentModelSettings = Field(
        default_factory=lambda: AgentModelSettings(model_name="gpt-3.5-turbo")
    )
    summarizer_model: AgentModelSettings = Field(
        default_factory=lambda: AgentModelSettings(model_name="gpt-3.5-turbo")
    )

    def __init__(self, **data):
        super().__init__(**data)
        if getattr(self, "planner_model_role", None) and not getattr(
            self, "planner_model", None
        ):
            self.planner_model = self.planner_model_role
        if getattr(self, "summarizer_model", None) and not getattr(
            self, "analyst_model", None
        ):
            self.analyst_model = self.summarizer_model


class AppSettings(BaseModel):
    theme: str = "light"
    language: str = "zh-CN"
    auto_connect: bool = False
    default_ssh_port: int = 22
    terminal_font: str = "Monaco, Consolas, monospace"
    terminal_font_size: int = 14
    max_log_lines: int = 1000
    auto_save_interval: int = 30000
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    ui: UISettings = Field(default_factory=UISettings)
    ssh: SSHSettings = Field(default_factory=SSHSettings)
    ai: Optional[Dict[str, Any]] = None
    agent: Optional[AgentSettings] = Field(default_factory=AgentSettings)


# ==================== 设置管理 ====================


def get_app_data_dir() -> Path:
    """获取应用数据目录"""
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif platform.system() == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".local" / "share"

    app_data_dir = base / "lovelyres"
    app_data_dir.mkdir(parents=True, exist_ok=True)
    return app_data_dir


def get_settings_file_path() -> Path:
    """获取设置文件路径"""
    return get_app_data_dir() / "settings.json"


def load_settings() -> AppSettings:
    """加载应用设置"""
    settings_file = get_settings_file_path()

    if not settings_file.exists():
        print("设置文件不存在，返回默认设置")
        return AppSettings()

    try:
        content = settings_file.read_text(encoding="utf-8")
        settings = AppSettings.model_validate_json(content)
        print("成功加载应用设置")
        return settings
    except Exception as e:
        print(f"解析设置文件失败: {e}，返回默认设置")
        return AppSettings()


def save_settings(settings: AppSettings) -> None:
    """保存应用设置"""
    settings_file = get_settings_file_path()
    content = settings.model_dump_json(indent=2)
    settings_file.write_text(content, encoding="utf-8")
    print("成功保存应用设置")


def reset_settings() -> None:
    """重置设置到默认值"""
    save_settings(AppSettings())


def backup_settings() -> Path:
    """备份当前设置"""
    settings = load_settings()
    app_data_dir = get_app_data_dir()
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_file = app_data_dir / f"settings_backup_{timestamp}.json"
    content = settings.model_dump_json(indent=2)
    backup_file.write_text(content, encoding="utf-8")
    print(f"设置已备份到: {backup_file}")
    return backup_file


def restore_settings(backup_file: Path) -> None:
    """从备份恢复设置"""
    if not backup_file.exists():
        raise FileNotFoundError("备份文件不存在")

    content = backup_file.read_text(encoding="utf-8")
    settings = AppSettings.model_validate_json(content)
    save_settings(settings)
    print(f"设置已从备份恢复: {backup_file}")


def validate_settings(settings: AppSettings) -> None:
    """验证设置格式，不合法则抛出 ValueError"""
    if settings.theme not in ("light", "dark", "sakura"):
        raise ValueError("无效的主题设置")
    if settings.language not in ("zh-CN", "en-US"):
        raise ValueError("无效的语言设置")
    if not (0 < settings.default_ssh_port <= 65535):
        raise ValueError("无效的SSH端口设置")
    if not (8 <= settings.terminal_font_size <= 72):
        raise ValueError("无效的终端字体大小设置")
    if not (0 < settings.max_log_lines <= 100000):
        raise ValueError("无效的最大日志行数设置")
    if not (1000 <= settings.auto_save_interval <= 3600000):
        raise ValueError("无效的自动保存间隔设置")
    if not (60000 <= settings.security.session_timeout <= 86400000):
        raise ValueError("无效的会话超时设置")
    if not (200 <= settings.ui.sidebar_width <= 800):
        raise ValueError("无效的侧边栏宽度设置")
    if not (5000 <= settings.ssh.keep_alive_interval <= 300000):
        raise ValueError("无效的SSH保活间隔设置")
    if not (1000 <= settings.ssh.connection_timeout <= 600000):
        raise ValueError("无效的SSH连接超时设置")
    if not (0 < settings.ssh.max_retries <= 10):
        raise ValueError("无效的SSH最大重试次数设置")


def read_settings_file() -> str:
    """读取设置文件内容"""
    settings_file = get_settings_file_path()
    if settings_file.exists():
        return settings_file.read_text(encoding="utf-8")
    return ""


def write_settings_file(content: str) -> None:
    """写入设置文件内容"""
    settings_file = get_settings_file_path()
    settings_file.write_text(content, encoding="utf-8")
