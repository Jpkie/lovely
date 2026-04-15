"""文件安全分析模块 - 从 Rust file_analysis.rs 迁移"""

import re
from typing import Optional

from app.models.types import FileAnalysisResult
from app.services.ssh_manager import SSHManager


async def sftp_file_analysis(manager: SSHManager, path: str) -> FileAnalysisResult:
    """文件安全分析"""
    if not manager.is_connected():
        raise ConnectionError("没有活动的 SSH 连接")

    # 获取文件基本信息
    stat_cmd = f'stat -c "%F|%s|%a|%U|%G|%W|%Y|%X" "{path}" 2>/dev/null'
    stat_output = await manager.execute_command(stat_cmd)

    file_type = "unknown"
    size = 0
    permissions = ""
    owner = ""
    group = ""
    created = ""
    modified = ""
    accessed = ""

    if stat_output.exit_code == 0:
        parts = stat_output.output.strip().split("|")
        if len(parts) >= 8:
            file_type = parts[0]
            try:
                size = int(parts[1])
            except ValueError:
                pass
            permissions = parts[2]
            owner = parts[3]
            group = parts[4]
            # 时间戳
            for i, key in [(5, "created"), (6, "modified"), (7, "accessed")]:
                try:
                    ts = int(parts[i])
                    if ts > 0:
                        from datetime import datetime, timezone
                        dt = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                        if key == "created":
                            created = dt
                        elif key == "modified":
                            modified = dt
                        else:
                            accessed = dt
                except (ValueError, IndexError):
                    pass

    # 计算文件哈希
    hash_cmd = f'md5sum "{path}" 2>/dev/null && sha1sum "{path}" 2>/dev/null && sha256sum "{path}" 2>/dev/null'
    hash_output = await manager.execute_command(hash_cmd)

    hash_md5 = None
    hash_sha1 = None
    hash_sha256 = None
    hash_lines = hash_output.output.strip().split("\n")
    if len(hash_lines) >= 1 and hash_lines[0].strip():
        hash_md5 = hash_lines[0].split()[0] if hash_lines[0].split() else None
    if len(hash_lines) >= 2 and hash_lines[1].strip():
        hash_sha1 = hash_lines[1].split()[0] if hash_lines[1].split() else None
    if len(hash_lines) >= 3 and hash_lines[2].strip():
        hash_sha256 = hash_lines[2].split()[0] if hash_lines[2].split() else None

    # 检测特殊权限
    is_suid = False
    is_sgid = False
    is_world_writable = False
    is_hidden = path.split("/")[-1].startswith(".")

    if permissions:
        try:
            perm_int = int(permissions, 8)
            is_suid = bool(perm_int & 0o4000)
            is_sgid = bool(perm_int & 0o2000)
            is_world_writable = bool(perm_int & 0o0002)
        except ValueError:
            pass

    # 风险指标
    risk_indicators = []
    if is_suid:
        risk_indicators.append("SUID位已设置")
    if is_sgid:
        risk_indicators.append("SGID位已设置")
    if is_world_writable:
        risk_indicators.append("全局可写")
    if is_hidden:
        risk_indicators.append("隐藏文件")

    # 检测文件内容中的可疑模式（仅对小文件）
    risk_level = "low"
    if size < 1024 * 1024:  # 小于1MB
        content_cmd = f'head -c 1048576 "{path}" 2>/dev/null'
        content_output = await manager.execute_command(content_cmd)
        content = content_output.output

        suspicious_patterns = [
            (r'eval\s*\(', "使用eval()"),
            (r'exec\s*\(', "使用exec()"),
            (r'system\s*\(', "使用system()"),
            (r'os\.system', "使用os.system"),
            (r'subprocess', "使用subprocess"),
            (r'rm\s+-rf', "危险rm命令"),
            (r'chmod\s+777', "危险chmod"),
            (r'/etc/passwd', "访问passwd文件"),
            (r'/etc/shadow', "访问shadow文件"),
        ]

        for pattern, desc in suspicious_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                risk_indicators.append(desc)

    if len(risk_indicators) >= 3:
        risk_level = "high"
    elif risk_indicators:
        risk_level = "medium"

    return FileAnalysisResult(
        path=path,
        file_type=file_type,
        size=size,
        permissions=permissions,
        owner=owner,
        group=group,
        hash_md5=hash_md5,
        hash_sha1=hash_sha1,
        hash_sha256=hash_sha256,
        modified=modified,
        created=created,
        accessed=accessed,
        is_suid=is_suid,
        is_sgid=is_sgid,
        is_world_writable=is_world_writable,
        is_hidden=is_hidden,
        risk_indicators=risk_indicators,
        risk_level=risk_level,
        details=f"发现 {len(risk_indicators)} 个风险指标" if risk_indicators else "未发现风险",
    )


async def sftp_file_analysis_independent(manager: SSHManager, path: str) -> FileAnalysisResult:
    """独立文件分析（不阻塞）- 与 sftp_file_analysis 相同实现"""
    return await sftp_file_analysis(manager, path)
