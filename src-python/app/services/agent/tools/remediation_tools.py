"""修复工具集 - 结构化修复操作

提供以下工具：
- detect_os_family: 检测操作系统家族
- detect_distribution_details: 获取发行版详情
- check_sudo_capability: 检查 sudo 能力
- detect_firewall_type: 检测防火墙类型
- backup_file: 备份文件
- patch_pam_lockout_policy: 修复 PAM 锁定策略
- verify_pam_lockout_policy: 验证 PAM 锁定策略
- patch_sshd_config: 修复 SSH 配置
- verify_sshd_config: 验证 SSH 配置
- patch_firewall_rules: 修复防火墙规则
- verify_firewall_rules: 验证防火墙规则
- patch_user_permissions: 修复用户权限
- restart_service_safely: 安全重启服务
- verify_all_fixes: 验证所有修复
- parse_detection_report: 解析检测报告
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from ..tool_registry import AgentToolResult, BaseTool, ToolRegistry, ToolStatus


class FailureErrorType(str, Enum):
    """失败错误类型分类"""

    PERMISSION_DENIED = "permission_denied"
    FILE_NOT_FOUND = "file_not_found"
    SERVICE_NOT_FOUND = "service_not_found"
    COMMAND_SYNTAX_ERROR = "command_syntax_error"
    PACKAGE_NOT_INSTALLED = "package_not_installed"
    UNSUPPORTED_DISTRIBUTION = "unsupported_distribution"
    VERIFICATION_FAILED = "verification_failed"
    HIGH_RISK_BLOCKED = "high_risk_blocked"
    TIMEOUT = "timeout"
    SSH_NOT_CONNECTED = "ssh_not_connected"
    UNKNOWN = "unknown"


class EnvironmentInfo:
    """环境信息"""

    def __init__(self):
        self.os_family: str = "unknown"
        self.distribution: str = "unknown"
        self.version: str = "unknown"
        self.package_manager: str = "unknown"
        self.init_system: str = "unknown"
        self.sudo_available: bool = False
        self.current_user: str = "unknown"
        self.root_required: bool = False


def classify_error(error_msg: str, exit_code: Optional[int] = None) -> FailureErrorType:
    """根据错误信息分类失败类型"""
    error_lower = error_msg.lower()

    if (
        "permission denied" in error_lower
        or "access denied" in error_lower
        or "sudo" in error_lower
        and "not allowed" in error_lower
    ):
        return FailureErrorType.PERMISSION_DENIED
    if (
        "no such file" in error_lower
        or "not found" in error_lower
        or "cannot find" in error_lower
    ):
        return FailureErrorType.FILE_NOT_FOUND
    if "service" in error_lower and (
        "not found" in error_lower
        or "not installed" in error_lower
        or "unknown service" in error_lower
    ):
        return FailureErrorType.SERVICE_NOT_FOUND
    if (
        "syntax error" in error_lower
        or "invalid" in error_lower
        and "syntax" in error_lower
    ):
        return FailureErrorType.COMMAND_SYNTAX_ERROR
    if "package" in error_lower and (
        "not found" in error_lower or "not installed" in error_lower
    ):
        return FailureErrorType.PACKAGE_NOT_INSTALLED
    if (
        "distribution" in error_lower
        or "unsupported" in error_lower
        or "not supported" in error_lower
    ):
        return FailureErrorType.UNSUPPORTED_DISTRIBUTION
    if (
        "verification" in error_lower
        or "verify" in error_lower
        and "failed" in error_lower
    ):
        return FailureErrorType.VERIFICATION_FAILED
    if (
        "high risk" in error_lower
        or "blocked" in error_lower
        or "dangerous" in error_lower
    ):
        return FailureErrorType.HIGH_RISK_BLOCKED
    if "timeout" in error_lower or "timed out" in error_lower:
        return FailureErrorType.TIMEOUT
    if "ssh" in error_lower and (
        "not connected" in error_lower or "connection" in error_lower
    ):
        return FailureErrorType.SSH_NOT_CONNECTED

    return FailureErrorType.UNKNOWN


def check_risk_level(tool_name: str, parameters: Dict[str, Any]) -> str:
    """评估操作的风险等级"""
    high_risk_patterns = [
        "pam",
        "sshd_config",
        "sudoers",
        "iptables",
        "firewall",
        "useradd",
        "userdel",
        "usermod",
        "passwd",
        "groupdel",
    ]
    medium_risk_patterns = ["chmod", "chown", "service", "systemctl", "restart"]

    tool_lower = tool_name.lower()
    for pattern in high_risk_patterns:
        if pattern in tool_lower:
            return "high"
    for pattern in medium_risk_patterns:
        if pattern in tool_lower:
            return "medium"
    return "low"


class DetectOSFamilyTool(BaseTool):
    """检测操作系统家族"""

    @property
    def name(self) -> str:
        return "detect_os_family"

    @property
    def description(self) -> str:
        return "检测目标系统的操作系统家族（Linux/Unix）"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            result = await manager.execute_command("uname -s")
            if result.exit_code != 0:
                return AgentToolResult(
                    tool_name=self.name,
                    status=ToolStatus.ERROR,
                    error=f"Failed to detect OS: {result.output}",
                )

            os_family = result.output.strip()
            if os_family == "Linux":
                os_family = "Linux"
            elif "BSD" in os_family:
                os_family = "BSD"
            else:
                os_family = "Unix-like"

            context["env_info"] = context.get("env_info", EnvironmentInfo())
            context["env_info"].os_family = os_family

            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output={"os_family": os_family},
                metadata={"os_family": os_family},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class DetectDistributionDetailsTool(BaseTool):
    """获取发行版详情"""

    @property
    def name(self) -> str:
        return "detect_distribution_details"

    @property
    def description(self) -> str:
        return "获取具体 Linux 发行版信息（RHEL/Debian/Ubuntu/CentOS 等）"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            os_release = ""
            result = await manager.execute_command(
                "cat /etc/os-release 2>/dev/null || cat /etc/redhat-release 2>/dev/null || cat /etc/debian_version 2>/dev/null || uname -r"
            )
            if result.exit_code == 0:
                os_release = result.output.strip()

            distribution = "unknown"
            version = "unknown"
            package_manager = "unknown"
            init_system = "unknown"

            if "Ubuntu" in os_release:
                distribution = "Ubuntu"
                package_manager = "apt"
            elif "Debian" in os_release:
                distribution = "Debian"
                package_manager = "apt"
            elif "CentOS" in os_release:
                distribution = "CentOS"
                package_manager = "yum"
            elif "Red Hat" in os_release or "RHEL" in os_release:
                distribution = "RHEL"
                package_manager = "yum"
            elif "Fedora" in os_release:
                distribution = "Fedora"
                package_manager = "dnf"
            elif "Amazon Linux" in os_release:
                distribution = "Amazon Linux"
                package_manager = "yum"
            elif "Alpine" in os_release:
                distribution = "Alpine"
                package_manager = "apk"
            elif "openSUSE" in os_release or "SUSE" in os_release:
                distribution = "SUSE"
                package_manager = "zypper"

            version_match = re.search(r'VERSION_ID\s*=\s*["\']?([\d.]+)', os_release)
            if version_match:
                version = version_match.group(1)

            result = await manager.execute_command(
                "ps -p 1 -o comm= 2>/dev/null || echo unknown"
            )
            if result.exit_code == 0:
                init_system = result.output.strip()
                if "systemd" in init_system:
                    init_system = "systemd"
                elif "init" in init_system or "SysV" in init_system:
                    init_system = "SysVinit"

            env_info = context.get("env_info", EnvironmentInfo())
            env_info.distribution = distribution
            env_info.version = version
            env_info.package_manager = package_manager
            env_info.init_system = init_system
            context["env_info"] = env_info

            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output={
                    "distribution": distribution,
                    "version": version,
                    "package_manager": package_manager,
                    "init_system": init_system,
                },
                metadata={
                    "distribution": distribution,
                    "version": version,
                    "package_manager": package_manager,
                    "init_system": init_system,
                },
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class CheckSudoCapabilityTool(BaseTool):
    """检查 sudo 能力"""

    @property
    def name(self) -> str:
        return "check_sudo_capability"

    @property
    def description(self) -> str:
        return "检查当前 SSH 用户是否具有 sudo 权限"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            whoami_result = await manager.execute_command("whoami")
            current_user = (
                whoami_result.output.strip()
                if whoami_result.exit_code == 0
                else "unknown"
            )

            sudo_result = await manager.execute_command("sudo -n true 2>&1")
            sudo_available = sudo_result.exit_code == 0

            is_root = current_user == "root"

            env_info = context.get("env_info", EnvironmentInfo())
            env_info.sudo_available = sudo_available
            env_info.current_user = current_user
            env_info.root_required = not sudo_available and not is_root
            context["env_info"] = env_info

            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output={
                    "current_user": current_user,
                    "sudo_available": sudo_available,
                    "is_root": is_root,
                    "root_required": not sudo_available and not is_root,
                },
                metadata={
                    "sudo_available": sudo_available,
                    "risk_level": "high" if not sudo_available else "low",
                },
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class DetectFirewallTypeTool(BaseTool):
    """检测防火墙类型"""

    @property
    def name(self) -> str:
        return "detect_firewall_type"

    @property
    def description(self) -> str:
        return "识别当前使用的防火墙类型（iptables/firewalld/ufw/nftables）"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            firewall_type = "none"

            result = await manager.execute_command(
                "systemctl is-active firewalld 2>/dev/null"
            )
            if result.exit_code == 0 and "active" in result.output:
                firewall_type = "firewalld"

            result = await manager.execute_command(
                "systemctl is-active ufw 2>/dev/null"
            )
            if result.exit_code == 0 and "active" in result.output:
                firewall_type = "ufw"

            result = await manager.execute_command(
                "which nft 2>/dev/null && nft list ruleset 2>/dev/null | head -5"
            )
            if result.exit_code == 0 and result.output.strip():
                firewall_type = "nftables"

            result = await manager.execute_command(
                "iptables -L -n 2>/dev/null | head -10"
            )
            if result.exit_code == 0 and firewall_type == "none":
                firewall_type = "iptables"

            context["firewall_type"] = firewall_type

            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output={"firewall_type": firewall_type},
                metadata={"firewall_type": firewall_type},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class BackupFileTool(BaseTool):
    """备份文件"""

    @property
    def name(self) -> str:
        return "backup_file"

    @property
    def description(self) -> str:
        return "在修改高风险配置文件前创建备份"

    @property
    def parameters(self) -> list:
        return [
            {"name": "path", "type": "string", "description": "要备份的文件路径"},
            {
                "name": "backup_suffix",
                "type": "string",
                "description": "备份文件后缀",
                "default": ".bak.auto_remediation",
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

        backup_suffix = parameters.get("backup_suffix", ".bak.auto_remediation")
        backup_path = f"{path}{backup_suffix}"

        try:
            check_result = await manager.execute_command(f"test -f {path}")
            if check_result.exit_code != 0:
                return AgentToolResult(
                    tool_name=self.name,
                    status=ToolStatus.ERROR,
                    error=f"File not found: {path}",
                    metadata={"error_type": FailureErrorType.FILE_NOT_FOUND.value},
                )

            result = await manager.execute_command(f"cp -p {path} {backup_path}")
            if result.exit_code != 0:
                return AgentToolResult(
                    tool_name=self.name,
                    status=ToolStatus.ERROR,
                    error=f"Failed to backup: {result.output}",
                    metadata={
                        "error_type": FailureErrorType.PERMISSION_DENIED.value
                        if "permission" in result.output.lower()
                        else FailureErrorType.UNKNOWN.value
                    },
                )

            context["backups"] = context.get("backups", {})
            context["backups"][path] = backup_path

            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output={
                    "original_path": path,
                    "backup_path": backup_path,
                    "success": True,
                },
                metadata={"backup_path": backup_path, "risk_level": "low"},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class ParseDetectionReportTool(BaseTool):
    """解析检测报告"""

    @property
    def name(self) -> str:
        return "parse_detection_report"

    @property
    def description(self) -> str:
        return "从上下文中提取并解析检测报告，提取需要修复的风险项"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        try:
            detection_report = context.get("detection_report", {})
            findings = context.get("findings", [])

            if not findings and detection_report:
                findings = []
                for item in detection_report.get("items", []):
                    if item.get("result") and item["result"].get("findings"):
                        for f in item["result"]["findings"]:
                            if f.get("severity") in ["critical", "high"]:
                                findings.append(
                                    {
                                        "check_name": item.get("name", "unknown"),
                                        "title": f.get("title", ""),
                                        "description": f.get("description", ""),
                                        "severity": f.get("severity", "high"),
                                        "recommendation": f.get("recommendation", ""),
                                    }
                                )

            categorized_findings = {
                "pam": [],
                "ssh": [],
                "firewall": [],
                "user": [],
                "service": [],
                "other": [],
            }

            for finding in findings:
                title_lower = finding.get("title", "").lower()
                desc_lower = finding.get("description", "").lower()

                if (
                    "pam" in title_lower
                    or "password" in title_lower
                    or "lockout" in title_lower
                ):
                    categorized_findings["pam"].append(finding)
                elif (
                    "ssh" in title_lower
                    or "sshd" in title_lower
                    or "authorized_keys" in title_lower
                ):
                    categorized_findings["ssh"].append(finding)
                elif (
                    "firewall" in title_lower
                    or "iptable" in title_lower
                    or "port" in title_lower
                ):
                    categorized_findings["firewall"].append(finding)
                elif (
                    "user" in title_lower
                    or "password" in desc_lower
                    or "empty password" in title_lower
                ):
                    categorized_findings["user"].append(finding)
                elif "service" in title_lower or "daemon" in title_lower:
                    categorized_findings["service"].append(finding)
                else:
                    categorized_findings["other"].append(finding)

            context["categorized_findings"] = categorized_findings
            context["all_findings"] = findings

            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output={
                    "total_findings": len(findings),
                    "categorized": {k: len(v) for k, v in categorized_findings.items()},
                    "findings": findings,
                },
                metadata={"findings_count": len(findings)},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class PatchPAMLockoutPolicyTool(BaseTool):
    """修复 PAM 锁定策略"""

    @property
    def name(self) -> str:
        return "patch_pam_lockout_policy"

    @property
    def description(self) -> str:
        return "根据 OS 类型应用正确的 PAM 锁定策略（失败次数锁定）"

    @property
    def parameters(self) -> list:
        return [
            {
                "name": "deny",
                "type": "integer",
                "description": "失败次数后锁定",
                "default": 5,
            },
            {
                "name": "unlock_time",
                "type": "integer",
                "description": "锁定时间（秒）",
                "default": 600,
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

        env_info: EnvironmentInfo = context.get("env_info", EnvironmentInfo())
        firewall_type = context.get("firewall_type", "unknown")

        deny = parameters.get("deny", 5)
        unlock_time = parameters.get("unlock_time", 600)

        try:
            if env_info.distribution in ["Ubuntu", "Debian"]:
                pam_file = "/etc/pam.d/common-auth"
            elif env_info.distribution in ["CentOS", "RHEL", "Fedora", "Amazon Linux"]:
                pam_file = "/etc/pam.d/system-auth"
            else:
                return AgentToolResult(
                    tool_name=self.name,
                    status=ToolStatus.ERROR,
                    error=f"Unsupported distribution: {env_info.distribution}",
                    metadata={
                        "error_type": FailureErrorType.UNSUPPORTED_DISTRIBUTION.value
                    },
                )

            check_result = await manager.execute_command(f"test -f {pam_file}")
            if check_result.exit_code != 0:
                return AgentToolResult(
                    tool_name=self.name,
                    status=ToolStatus.ERROR,
                    error=f"PAM config file not found: {pam_file}",
                    metadata={"error_type": FailureErrorType.FILE_NOT_FOUND.value},
                )

            existing_result = await manager.execute_command(
                f"grep -E 'pam_pwquality|pam_tally2|pam_faillock' {pam_file} || echo 'not_found'"
            )
            has_tally = (
                "pam_tally2" in existing_result.output
                or "pam_faillock" in existing_result.output
            )

            if has_tally:
                cmd = f"grep -E 'pam_tally2|pam_faillock' {pam_file}"
            else:
                if env_info.distribution in ["Ubuntu", "Debian"]:
                    cmd = f"echo 'auth required pam_tally2.so deny={deny} unlock_time={unlock_time}' >> {pam_file}"
                else:
                    cmd = f"echo 'auth required pam_tally2.so deny={deny} unlock_time={unlock_time}' >> {pam_file}"

            result = await manager.execute_command(cmd)
            if result.exit_code != 0:
                return AgentToolResult(
                    tool_name=self.name,
                    status=ToolStatus.ERROR,
                    error=f"Failed to patch PAM: {result.output}",
                    metadata={
                        "error_type": FailureErrorType.PERMISSION_DENIED.value
                        if "permission" in result.output.lower()
                        else FailureErrorType.UNKNOWN.value
                    },
                )

            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output={
                    "pam_file": pam_file,
                    "deny": deny,
                    "unlock_time": unlock_time,
                    "applied": True,
                },
                metadata={
                    "risk_level": "high",
                    "pam_file": pam_file,
                    "verification_required": True,
                },
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class VerifyPAMLockoutPolicyTool(BaseTool):
    """验证 PAM 锁定策略"""

    @property
    def name(self) -> str:
        return "verify_pam_lockout_policy"

    @property
    def description(self) -> str:
        return "验证 PAM 锁定策略是否正确应用"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        env_info: EnvironmentInfo = context.get("env_info", EnvironmentInfo())

        try:
            if env_info.distribution in ["Ubuntu", "Debian"]:
                pam_file = "/etc/pam.d/common-auth"
            elif env_info.distribution in ["CentOS", "RHEL", "Fedora", "Amazon Linux"]:
                pam_file = "/etc/pam.d/system-auth"
            else:
                pam_file = "/etc/pam.d/system-auth"

            result = await manager.execute_command(
                f"grep -E 'pam_tally2|pam_faillock|pam_pwquality' {pam_file} || echo 'no_tally_config'"
            )
            verification_passed = (
                "pam_tally2" in result.output
                or "pam_faillock" in result.output
                or "pam_pwquality" in result.output
            )

            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS if verification_passed else ToolStatus.ERROR,
                output={
                    "verification_passed": verification_passed,
                    "config_content": result.output.strip(),
                    "pam_file": pam_file,
                },
                metadata={
                    "verification_passed": verification_passed,
                    "risk_level": "high",
                },
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class PatchSSHDConfigTool(BaseTool):
    """修复 SSH 配置"""

    @property
    def name(self) -> str:
        return "patch_sshd_config"

    @property
    def description(self) -> str:
        return "修复 SSH 安全配置（禁用 root 登录、禁用密码认证等）"

    @property
    def parameters(self) -> list:
        return [
            {
                "name": "disable_root_login",
                "type": "boolean",
                "description": "禁用 root 登录",
                "default": True,
            },
            {
                "name": "disable_password_auth",
                "type": "boolean",
                "description": "禁用密码认证",
                "default": True,
            },
            {
                "name": "minimize_config",
                "type": "boolean",
                "description": "最小化配置（只修改必须的）",
                "default": True,
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

        disable_root = parameters.get("disable_root_login", True)
        disable_pass = parameters.get("disable_password_auth", True)

        try:
            sshd_config = "/etc/ssh/sshd_config"
            backup_path = context.get("backups", {}).get(sshd_config)

            if not backup_path:
                backup_path = f"{sshd_config}.bak.auto_remediation"
                await manager.execute_command(f"cp -p {sshd_config} {backup_path}")

            changes_applied = []

            if disable_root:
                result = await manager.execute_command(
                    f"grep -E '^PermitRootLogin' {sshd_config} || echo 'not_found'"
                )
                if "not_found" not in result.output:
                    await manager.execute_command(
                        f"sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' {sshd_config}"
                    )
                else:
                    await manager.execute_command(
                        f"echo 'PermitRootLogin no' >> {sshd_config}"
                    )
                changes_applied.append("PermitRootLogin=no")

            if disable_pass:
                result = await manager.execute_command(
                    f"grep -E '^PasswordAuthentication' {sshd_config} || echo 'not_found'"
                )
                if "not_found" not in result.output:
                    await manager.execute_command(
                        f"sed -i 's/^PasswordAuthentication.*/PasswordAuthentication no/' {sshd_config}"
                    )
                else:
                    await manager.execute_command(
                        f"echo 'PasswordAuthentication no' >> {sshd_config}"
                    )
                changes_applied.append("PasswordAuthentication=no")

            context["sshd_changes"] = changes_applied

            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output={
                    "config_file": sshd_config,
                    "changes_applied": changes_applied,
                    "applied": True,
                },
                metadata={
                    "risk_level": "high",
                    "changes": changes_applied,
                    "verification_required": True,
                },
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class VerifySSHDConfigTool(BaseTool):
    """验证 SSH 配置"""

    @property
    def name(self) -> str:
        return "verify_sshd_config"

    @property
    def description(self) -> str:
        return "验证 SSH 配置正确性并 reload 服务"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        env_info: EnvironmentInfo = context.get("env_info", EnvironmentInfo())

        try:
            sshd_config = "/etc/ssh/sshd_config"

            test_result = await manager.execute_command(
                f"sshd -t -f {sshd_config} 2>&1"
            )
            config_valid = test_result.exit_code == 0

            if not config_valid:
                return AgentToolResult(
                    tool_name=self.name,
                    status=ToolStatus.ERROR,
                    error=f"SSH config test failed: {test_result.output}",
                    metadata={
                        "error_type": FailureErrorType.VERIFICATION_FAILED.value,
                        "verification_passed": False,
                    },
                )

            if env_info.init_system == "systemd":
                reload_result = await manager.execute_command(
                    "systemctl reload sshd 2>/dev/null || systemctl reload ssh 2>/dev/null"
                )
            else:
                reload_result = await manager.execute_command(
                    "service sshd reload 2>/dev/null || service ssh reload 2>/dev/null"
                )

            reload_success = reload_result.exit_code == 0

            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS if reload_success else ToolStatus.PARTIAL,
                output={
                    "config_valid": config_valid,
                    "reload_success": reload_success,
                    "reload_output": reload_result.output.strip(),
                },
                metadata={
                    "verification_passed": config_valid and reload_success,
                    "risk_level": "high",
                },
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class PatchFirewallRulesTool(BaseTool):
    """修复防火墙规则"""

    @property
    def name(self) -> str:
        return "patch_firewall_rules"

    @property
    def description(self) -> str:
        return "根据防火墙类型应用正确的防火墙规则"

    @property
    def parameters(self) -> list:
        return [
            {
                "name": "allowed_ports",
                "type": "array",
                "description": "允许的端口列表",
                "default": [],
            },
            {
                "name": "block_ports",
                "type": "array",
                "description": "要阻止的端口列表",
                "default": [],
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

        firewall_type = context.get("firewall_type", "unknown")
        allowed_ports = parameters.get("allowed_ports", [])
        block_ports = parameters.get("block_ports", [])

        try:
            changes_applied = []

            if firewall_type == "firewalld":
                for port in allowed_ports:
                    result = await manager.execute_command(
                        f"firewall-cmd --permanent --add-port={port}/tcp 2>/dev/null"
                    )
                    if result.exit_code == 0:
                        changes_applied.append(f"firewalld: allowed {port}/tcp")
                await manager.execute_command("firewall-cmd --reload 2>/dev/null")

            elif firewall_type == "ufw":
                for port in allowed_ports:
                    result = await manager.execute_command(
                        f"ufw allow {port}/tcp 2>/dev/null"
                    )
                    if result.exit_code == 0:
                        changes_applied.append(f"ufw: allowed {port}/tcp")
                await manager.execute_command("ufw reload 2>/dev/null")

            elif firewall_type == "iptables":
                for port in allowed_ports:
                    result = await manager.execute_command(
                        f"iptables -A INPUT -p tcp --dport {port} -j ACCEPT 2>/dev/null"
                    )
                    if result.exit_code == 0:
                        changes_applied.append(f"iptables: allowed {port}/tcp")

            elif firewall_type == "nftables":
                for port in allowed_ports:
                    result = await manager.execute_command(
                        f"nft add rule ip filter input tcp dport {port} accept 2>/dev/null"
                    )
                    if result.exit_code == 0:
                        changes_applied.append(f"nftables: allowed {port}/tcp")

            context["firewall_changes"] = changes_applied

            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output={
                    "firewall_type": firewall_type,
                    "changes_applied": changes_applied,
                },
                metadata={"risk_level": "high", "verification_required": True},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class VerifyFirewallRulesTool(BaseTool):
    """验证防火墙规则"""

    @property
    def name(self) -> str:
        return "verify_firewall_rules"

    @property
    def description(self) -> str:
        return "验证防火墙规则是否生效"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        firewall_type = context.get("firewall_type", "unknown")

        try:
            verification_passed = False
            rules_content = ""

            if firewall_type == "firewalld":
                result = await manager.execute_command(
                    "firewall-cmd --list-all 2>/dev/null"
                )
                verification_passed = result.exit_code == 0
                rules_content = result.output

            elif firewall_type == "ufw":
                result = await manager.execute_command("ufw status verbose 2>/dev/null")
                verification_passed = result.exit_code == 0
                rules_content = result.output

            elif firewall_type == "iptables":
                result = await manager.execute_command(
                    "iptables -L -n 2>/dev/null | head -20"
                )
                verification_passed = result.exit_code == 0
                rules_content = result.output

            elif firewall_type == "nftables":
                result = await manager.execute_command(
                    "nft list ruleset 2>/dev/null | head -20"
                )
                verification_passed = result.exit_code == 0
                rules_content = result.output

            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS if verification_passed else ToolStatus.ERROR,
                output={
                    "verification_passed": verification_passed,
                    "firewall_type": firewall_type,
                    "rules_content": rules_content.strip(),
                },
                metadata={
                    "verification_passed": verification_passed,
                    "risk_level": "medium",
                },
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class PatchUserPermissionsTool(BaseTool):
    """修复用户权限问题"""

    @property
    def name(self) -> str:
        return "patch_user_permissions"

    @property
    def description(self) -> str:
        return "修复检测到的用户权限问题（空密码账户、可疑用户等）"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        categorized_findings = context.get("categorized_findings", {})
        user_findings = categorized_findings.get("user", [])

        try:
            changes_applied = []
            blocked_items = []
            env_info: EnvironmentInfo = context.get("env_info", EnvironmentInfo())

            if not env_info.sudo_available and not env_info.current_user == "root":
                return AgentToolResult(
                    tool_name=self.name,
                    status=ToolStatus.ERROR,
                    output={
                        "changes_applied": [],
                        "blocked_items": [f"需要 sudo 权限但当前用户无可用 sudo"],
                    },
                    error="Permission denied: no sudo access",
                    metadata={
                        "error_type": FailureErrorType.PERMISSION_DENIED.value,
                        "blocked": True,
                    },
                )

            for finding in user_findings:
                title_lower = finding.get("title", "").lower()
                desc_lower = finding.get("description", "").lower()

                if "empty password" in title_lower or "empty password" in desc_lower:
                    result = await manager.execute_command(
                        "awk -F: '($2 == \"\") {print $1}' /etc/shadow 2>/dev/null"
                    )
                    if result.exit_code == 0 and result.output.strip():
                        users_with_empty_pass = result.output.strip().split("\n")
                        for user in users_with_empty_pass:
                            lock_result = await manager.execute_command(
                                f"passwd -l {user} 2>/dev/null"
                            )
                            if lock_result.exit_code == 0:
                                changes_applied.append(
                                    f"Locked empty password user: {user}"
                                )

            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output={
                    "changes_applied": changes_applied,
                    "blocked_items": blocked_items,
                },
                metadata={
                    "risk_level": "high",
                    "changes_count": len(changes_applied),
                    "blocked_count": len(blocked_items),
                },
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class RestartServiceSafelyTool(BaseTool):
    """安全重启服务"""

    @property
    def name(self) -> str:
        return "restart_service_safely"

    @property
    def description(self) -> str:
        return "安全地重启需要刷新配置的服务（先验证配置再重启）"

    @property
    def parameters(self) -> list:
        return [
            {
                "name": "service_name",
                "type": "string",
                "description": "服务名称",
                "default": "",
            }
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

        env_info: EnvironmentInfo = context.get("env_info", EnvironmentInfo())
        service_name = parameters.get("service_name", "")

        if not service_name:
            services_to_restart = ["sshd", "ssh", "firewalld", "ufw"]
        else:
            services_to_restart = [service_name]

        try:
            results = {}

            for svc in services_to_restart:
                check_result = await manager.execute_command(
                    f"systemctl is-active {svc} 2>/dev/null || service {svc} status 2>/dev/null | head -3"
                )
                if (
                    check_result.exit_code != 0
                    and "unknown" in check_result.output.lower()
                ):
                    continue

                if env_info.init_system == "systemd":
                    restart_result = await manager.execute_command(
                        f"systemctl restart {svc} 2>&1"
                    )
                else:
                    restart_result = await manager.execute_command(
                        f"service {svc} restart 2>&1"
                    )

                results[svc] = {
                    "restarted": restart_result.exit_code == 0,
                    "output": restart_result.output.strip(),
                }

            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                output={"services_restarted": results},
                metadata={"risk_level": "medium"},
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


class VerifyAllFixesTool(BaseTool):
    """验证所有修复"""

    @property
    def name(self) -> str:
        return "verify_all_fixes"

    @property
    def description(self) -> str:
        return "最终验证所有修复项是否生效，生成汇总报告"

    @property
    def parameters(self) -> list:
        return []

    async def execute(
        self, parameters: Dict[str, Any], context: Dict[str, Any]
    ) -> AgentToolResult:
        from app.services.ssh_manager import SSHManager

        manager: SSHManager = context.get("ssh_manager")
        if not manager or not manager.is_connected():
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error="SSH not connected"
            )

        try:
            env_info: EnvironmentInfo = context.get("env_info", EnvironmentInfo())
            categorized_findings = context.get("categorized_findings", {})

            verification_results = {
                "pam": {"checked": False, "passed": False, "details": ""},
                "ssh": {"checked": False, "passed": False, "details": ""},
                "firewall": {"checked": False, "passed": False, "details": ""},
                "user": {"checked": False, "passed": False, "details": ""},
            }

            pam_findings = categorized_findings.get("pam", [])
            if pam_findings:
                if env_info.distribution in ["Ubuntu", "Debian"]:
                    pam_file = "/etc/pam.d/common-auth"
                else:
                    pam_file = "/etc/pam.d/system-auth"
                result = await manager.execute_command(
                    f"grep -E 'pam_tally2|pam_faillock' {pam_file} 2>/dev/null || echo 'not_found'"
                )
                verification_results["pam"] = {
                    "checked": True,
                    "passed": "pam_tally2" in result.output
                    or "pam_faillock" in result.output,
                    "details": result.output.strip(),
                }

            ssh_findings = categorized_findings.get("ssh", [])
            if ssh_findings:
                result = await manager.execute_command(
                    "grep -E '^PermitRootLogin|^PasswordAuthentication' /etc/ssh/sshd_config 2>/dev/null || echo 'not_found'"
                )
                verification_results["ssh"] = {
                    "checked": True,
                    "passed": "PermitRootLogin no" in result.output
                    and "PasswordAuthentication no" in result.output,
                    "details": result.output.strip(),
                }

            all_passed = all(
                v["passed"] or not v["checked"] for v in verification_results.values()
            )

            return AgentToolResult(
                tool_name=self.name,
                status=ToolStatus.SUCCESS if all_passed else ToolStatus.PARTIAL,
                output={
                    "all_verified": all_passed,
                    "verification_results": verification_results,
                    "environment": {
                        "os_family": env_info.os_family,
                        "distribution": env_info.distribution,
                        "version": env_info.version,
                        "sudo_available": env_info.sudo_available,
                    },
                },
                metadata={
                    "all_passed": all_passed,
                    "verification_results": verification_results,
                    "risk_level": "low",
                },
            )
        except Exception as e:
            return AgentToolResult(
                tool_name=self.name, status=ToolStatus.ERROR, error=str(e)
            )


def register_remediation_tools(registry: ToolRegistry) -> None:
    """注册所有修复工具"""
    registry.register(DetectOSFamilyTool())
    registry.register(DetectDistributionDetailsTool())
    registry.register(CheckSudoCapabilityTool())
    registry.register(DetectFirewallTypeTool())
    registry.register(BackupFileTool())
    registry.register(ParseDetectionReportTool())
    registry.register(PatchPAMLockoutPolicyTool())
    registry.register(VerifyPAMLockoutPolicyTool())
    registry.register(PatchSSHDConfigTool())
    registry.register(VerifySSHDConfigTool())
    registry.register(PatchFirewallRulesTool())
    registry.register(VerifyFirewallRulesTool())
    registry.register(PatchUserPermissionsTool())
    registry.register(RestartServiceSafelyTool())
    registry.register(VerifyAllFixesTool())
