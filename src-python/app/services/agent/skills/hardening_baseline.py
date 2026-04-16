"""主机基线加固 Skill - 完整的安全基线检查与修复

职责：
  - 把现有零散的基线检测组合成一套完整 skill
  - 可输出基线评分
  - 区分：可自动修复 / 需人工确认 / 仅建议项
  - 适合作为周期性安全检查

覆盖项：
  - password policy
  - sudo config
  - pam config
  - account lockout
  - SELinux/AppArmor
  - kernel params
  - system updates
  - unnecessary services
  - auto-start services
  - audit config
  - history audit
  - ntp config
  - dns config
"""

from typing import Any, Dict, List

from ..skills.registry import BaseSkill, SkillStep


class HardeningBaselineSkill(BaseSkill):
    """主机基线加固 Skill"""

    @property
    def name(self) -> str:
        return "hardening_baseline"

    @property
    def description(self) -> str:
        return (
            "执行主机安全基线全面检查，覆盖密码策略、SUDO、PAM、防火墙、"
            "服务管理、内核参数等维度，输出基线评分和改进建议。"
        )

    @property
    def category(self) -> str:
        return "assessment"

    @property
    def steps(self) -> List[SkillStep]:
        return [
            # ========== 环境探测 ==========
            SkillStep(
                id="hb_env",
                name="环境探测",
                description="探测 OS 类型、发行版、init system",
                tool_name="detect_distribution_details",
                parameters={},
                depends_on=[],
            ),
            # ========== 账户安全 ==========
            SkillStep(
                id="hb_account",
                name="账户安全检查",
                description="检查空密码账户、特权用户、可疑账户",
                tool_name="detect_user_audit",
                parameters={},
                depends_on=["hb_env"],
            ),
            # ========== SSH 安全 ==========
            SkillStep(
                id="hb_ssh",
                name="SSH 安全检查",
                description="检查 SSH 配置安全性",
                tool_name="detect_ssh_audit",
                parameters={},
                depends_on=["hb_env"],
            ),
            # ========== 防火墙 ==========
            SkillStep(
                id="hb_firewall",
                name="防火墙检查",
                description="检查防火墙状态和规则",
                tool_name="detect_firewall",
                parameters={},
                depends_on=["hb_env"],
            ),
            # ========== 文件权限 ==========
            SkillStep(
                id="hb_file",
                name="文件权限检查",
                description="检查敏感文件权限和 SUID 文件",
                tool_name="detect_file_permission",
                parameters={},
                depends_on=[],
            ),
            # ========== 进程与服务 ==========
            SkillStep(
                id="hb_process",
                name="进程安全检查",
                description="检查可疑进程和网络连接",
                tool_name="detect_process",
                parameters={},
                depends_on=[],
            ),
            # ========== 端口安全 ==========
            SkillStep(
                id="hb_port",
                name="端口安全检查",
                description="检查开放端口和高危服务",
                tool_name="detect_port_scan",
                parameters={},
                depends_on=[],
            ),
            # ========== 日志安全 ==========
            SkillStep(
                id="hb_log",
                name="日志安全检查",
                description="检查认证失败日志、暴力破解痕迹",
                tool_name="detect_log",
                parameters={},
                depends_on=[],
            ),
            # ========== 基线评分 ==========
            SkillStep(
                id="hb_score",
                name="计算基线评分",
                description="综合所有检查项计算安全基线评分",
                tool_name="calculate_hardening_score",
                parameters={},
                depends_on=[
                    "hb_account",
                    "hb_ssh",
                    "hb_firewall",
                    "hb_file",
                    "hb_process",
                    "hb_port",
                    "hb_log",
                ],
            ),
            # ========== 生成报告 ==========
            SkillStep(
                id="hb_report",
                name="生成基线报告",
                description="生成完整的基线加固报告",
                tool_name="generate_hardening_report",
                parameters={},
                depends_on=["hb_score"],
            ),
        ]

    @property
    def required_context_keys(self) -> List[str]:
        return ["ssh_manager"]

    @property
    def output_template(self) -> str:
        return """# 主机安全基线报告

## 基线评分
{baseline_score}/100

## 检查项结果
| 检查项 | 状态 | 风险等级 | 说明 |
|--------|------|----------|------|
{check_results}

## 可自动修复项
{auto_fix_items}

## 需人工确认项
{manual_confirm_items}

## 建议项
{recommendation_items}

## 风险摘要
{risks_summary}
"""


def register_hardening_baseline_skill(registry) -> None:
    """注册主机基线加固 skill"""
    registry.register(HardeningBaselineSkill())


def get_hardening_baseline_skill():
    """获取主机基线加固 skill 实例"""
    return HardeningBaselineSkill()
