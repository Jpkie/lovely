"""窗口管理器 - 从 Rust window_manager.rs 迁移

在 Python 后端中，窗口管理通过 WebSocket 事件通知前端实现
"""

from typing import Any, Dict, Optional


class WindowManager:
    """窗口管理器

    由于 Python 后端无法直接控制 Tauri 窗口，
    窗口操作通过 WebSocket 事件通知前端执行
    """

    def __init__(self):
        self._windows: Dict[str, Dict[str, Any]] = {}

    def create_window(
        self, label: str, title: str, url: str, width: float = 900, height: float = 600
    ) -> Dict[str, Any]:
        """创建窗口（返回窗口信息，由前端执行创建）"""
        window_info = {
            "label": label,
            "title": title,
            "url": url,
            "width": width,
            "height": height,
        }
        self._windows[label] = window_info
        return window_info

    def get_window(self, label: str) -> Optional[Dict[str, Any]]:
        """获取窗口信息"""
        return self._windows.get(label)

    def close_window(self, label: str) -> bool:
        """关闭窗口"""
        if label in self._windows:
            del self._windows[label]
            return True
        return False

    def list_windows(self) -> Dict[str, Dict[str, Any]]:
        """列出所有窗口"""
        return self._windows.copy()
