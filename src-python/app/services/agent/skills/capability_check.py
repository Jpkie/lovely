"""环境能力检查 Skill - 在执行修复前先探测环境能力

职责：
  - 在执行修复前先探测环境能力
  - 避免执行过程中才发现 sudo/systemctl/firewall 工具不可用
  - 输出 capability matrix 和 blocked reasons

检查项：
  - OS 家族和发行版
  - sudo 是否可用
  - init system（systemd/openrc/sysvinit）
  - package manager（apt/yum/dnf/pacman/apk）
  - firewall stack（iptables/ufw/firewalld/nftables）
  - SELinux / AppArmor 状态
  - 目标配置文件是否存在
  - 是否有写权限

输出：
  - environment summary
  - capability matrix
  - blocked reasons
  - recommendations

状态语义：
  - completed: 环境能力探测完成
  - partially_completed: 部分能力可用
  - unsupported_environment: 环境不支持自动修复
"""

from typing import Any, Dict, List

from ..skills.registry import BaseSkill, SkillStep


class CapabilityCheckSkill(BaseSkill):
    """环境能力检查 Skill"""

    @property
    def name(self) -> str:
        return "capability_check"

    @property
    def description(self) -> str:
        return (
            "在执行修复前先探测环境能力，检查 sudo/工具/配置文件的可用性，"
            "输出 capability matrix 和 blocked reasons，避免修复中途失败。"
        )

    @property
    def category(self) -> str:
        return "investigation"

    @property
    def steps(self) -> List[SkillStep]:
        return [
            # ========== OS 和发行版检测 ==========
            SkillStep(
                id="cap_os",
                name="检测 OS 家族",
                description="识别目标系统的 OS 类型（Linux/Unix）",
                tool_name="detect_os_family",
                parameters={},
                depends_on=[],
            ),
            SkillStep(
                id="cap_distro",
                name="获取发行版详情",
                description="获取具体发行版信息（RHEL/Debian/Ubuntu 等）",
                tool_name="detect_distribution_details",
                parameters={},
                depends_on=["cap_os"],
            ),
            # ========== 权限能力检测 ==========
            SkillStep(
                id="cap_sudo",
                name="检查 sudo 能力",
                description="检查当前用户是否有 sudo 权限",
                tool_name="check_sudo_capability",
                parameters={},
                depends_on=["cap_os"],
            ),
            # ========== 防火墙能力检测 ==========
            SkillStep(
                id="cap_firewall",
                name="检测防火墙类型",
                description="识别当前使用的防火墙类型（iptables/firewalld/ufw/nftables）",
                tool_name="detect_firewall_type",
                parameters={},
                depends_on=["cap_os"],
            ),
            # ========== 关键文件存在性检测 ==========
            SkillStep(
                id="cap_files",
                name="检查关键文件",
                description="检查 SSH/PAM 等关键配置文件是否存在",
                tool_name="check_critical_files",
                parameters={},
                depends_on=["cap_distro"],
            ),
            # ========== 服务能力检测 ==========
            SkillStep(
                id="cap_services",
                name="检查服务管理能力",
                description="检查 systemctl/service 命令是否可用",
                tool_name="check_service_capability",
                parameters={},
                depends_on=["cap_os"],
            ),
            # ========== 生成能力报告 ==========
            SkillStep(
                id="cap_report",
                name="生成能力报告",
                description="汇总所有能力检测结果，生成 capability matrix",
                tool_name="generate_capability_report",
                parameters={},
                depends_on=[
                    "cap_distro",
                    "cap_sudo",
                    "cap_firewall",
                    "cap_files",
                    "cap_services",
                ],
            ),
        ]

    @property
    def required_context_keys(self) -> List[str]:
        return ["ssh_manager"]

    @property
    def output_template(self) -> str:
        return """# 环境能力检查报告

## 环境概要
{environment_summary}

## 能力矩阵
|capability|available|details|
|----------|---------|--------|
{sudo}|{sudo_available}|{sudo_details}|
|firewall|{firewall_type}|{firewall_details}|
|package_manager|{pkg_manager}|{pkg_details}|
|init_system|{init_system}|{init_details}|
|selinux|{selinux_status}|{selinux_details}|

## 阻止原因（如有）
{blocked_reasons}

## 建议
{recommendations}
"""


def register_capability_check_skill(registry) -> None:
    """注册环境能力检查 skill"""
    registry.register(CapabilityCheckSkill())


def get_capability_check_skill():
    """获取环境能力检查 skill 实例"""
    return CapabilityCheckSkill()
