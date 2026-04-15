"""系统字体获取模块 - 从 Rust lib.rs 中的字体获取逻辑迁移"""

import os
import platform
import subprocess
from typing import List


def get_default_fonts() -> List[str]:
    """获取默认字体列表"""
    return [
        "系统默认",
        # Windows 中文字体
        "Microsoft YaHei", "Microsoft YaHei UI", "微软雅黑",
        "SimSun", "宋体", "SimHei", "黑体", "KaiTi", "楷体",
        "FangSong", "仿宋", "Microsoft JhengHei", "微软正黑体",
        "DengXian", "等线", "YouYuan", "幼圆", "LiSu", "隶书",
        "STXihei", "华文细黑", "STKaiti", "华文楷体",
        "STSong", "华文宋体", "STFangsong", "华文仿宋",
        # macOS 中文字体
        "PingFang SC", "苹方", "Hiragino Sans GB", "冬青黑体简体中文",
        # 开源中文字体
        "Noto Sans CJK SC", "思源黑体", "Source Han Sans SC",
        "Noto Serif CJK SC", "思源宋体", "Source Han Serif SC",
        # Windows 英文字体
        "Arial", "Times New Roman", "Calibri", "Segoe UI",
        "Tahoma", "Verdana", "Georgia", "Trebuchet MS",
        "Comic Sans MS", "Impact", "Lucida Console", "Palatino Linotype",
        # 等宽字体
        "Consolas", "Courier New", "JetBrains Mono", "Fira Code",
        "Source Code Pro", "Monaco", "Menlo", "Inconsolata",
        "Roboto Mono", "Ubuntu Mono",
        # 设计字体
        "Helvetica", "Helvetica Neue", "San Francisco",
        "Roboto", "Open Sans", "Lato", "Montserrat", "Poppins",
    ]


def get_fonts_from_directory() -> List[str]:
    """从字体目录获取字体列表"""
    fonts = ["系统默认"]

    if platform.system() == "Windows":
        font_dirs = ["C:\\Windows\\Fonts", "C:\\Windows\\System32\\Fonts"]
    elif platform.system() == "Darwin":
        font_dirs = ["/Library/Fonts", "/System/Library/Fonts", os.path.expanduser("~/Library/Fonts")]
    else:
        font_dirs = ["/usr/share/fonts", "/usr/local/share/fonts", os.path.expanduser("~/.fonts")]

    for font_dir in font_dirs:
        if not os.path.isdir(font_dir):
            continue
        for filename in os.listdir(font_dir):
            if filename.endswith((".ttf", ".otf", ".ttc")):
                font_name = filename.replace(".ttf", "").replace(".otf", "").replace(".ttc", "")
                font_name = font_name.replace("_", " ").replace("-", " ")
                if font_name and font_name not in fonts:
                    fonts.append(font_name)

    fonts.sort()
    return fonts


def get_fonts_from_registry() -> List[str]:
    """从 Windows 注册表获取字体列表"""
    if platform.system() != "Windows":
        return []

    try:
        result = subprocess.run(
            ["reg", "query", "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            fonts = ["系统默认"]
            for line in result.stdout.split("\n"):
                if "REG_SZ" in line and line.strip():
                    parts = line.split("REG_SZ")
                    if parts:
                        font_entry = parts[0].strip()
                        font_name = (
                            font_entry.replace(" (TrueType)", "").replace(" (OpenType)", "")
                            .replace(" Bold", "").replace(" Italic", "")
                            .replace(" Regular", "").replace(" Light", "")
                            .replace(" Medium", "").strip()
                        )
                        if font_name and font_name not in fonts and len(font_name) > 1:
                            fonts.append(font_name)
            fonts.sort()
            return fonts
    except Exception:
        pass
    return []


def get_system_fonts() -> List[str]:
    """获取系统字体列表"""
    # 方法1: 从注册表获取 (Windows)
    if platform.system() == "Windows":
        fonts = get_fonts_from_registry()
        if len(fonts) > 10:
            return fonts

    # 方法2: 从字体目录获取
    fonts = get_fonts_from_directory()
    if len(fonts) > 10:
        return fonts

    # 方法3: 使用默认字体列表
    return get_default_fonts()
