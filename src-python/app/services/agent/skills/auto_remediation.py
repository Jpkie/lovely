"""自动修复 Skill - 基于检测报告生成结构化修复计划"""

from typing import Any, Dict, List

from ..skills.registry import BaseSkill, SkillStep


class AutoRemediationSkill(BaseSkill):
    """自动修复 Skill - 接收检测报告，生成并执行结构化修复计划"""

    @property
    def name(self) -> str:
        return "auto_remediation"

    @property
    def description(self) -> str:
        return "接收安全检测报告，自动分析风险项并执行结构化修复。支持环境识别、失败重规划、修复验证。"

    @property
    def category(self) -> str:
        return "remediation"

    @property
    def steps(self) -> List[SkillStep]:
        return [
            # 阶段1: 环境识别
            SkillStep(
                id="ar_env_1",
                name="检测 OS 家族",
                description="识别目标系统的 OS 类型（Linux/Unix）",
                tool_name="detect_os_family",
                parameters={},
                depends_on=[],
            ),
            SkillStep(
                id="ar_env_2",
                name="获取发行版详情",
                description="获取具体发行版信息（RHEL/Debian/Ubuntu 等）",
                tool_name="detect_distribution_details",
                parameters={},
                depends_on=["ar_env_1"],
            ),
            SkillStep(
                id="ar_env_3",
                name="检查 sudo 能力",
                description="检查当前用户是否有 sudo 权限",
                tool_name="check_sudo_capability",
                parameters={},
                depends_on=["ar_env_1"],
            ),
            # 阶段2: 解析修复任务
            SkillStep(
                id="ar_parse_1",
                name="解析检测报告",
                description="从上下文中提取检测报告和风险项",
                tool_name="parse_detection_report",
                parameters={},
                depends_on=["ar_env_2", "ar_env_3"],
            ),
            # 阶段3: 高风险操作修复（按风险等级排序）
            SkillStep(
                id="ar_fix_pam_1",
                name="备份 PAM 配置",
                description="修改 PAM 配置前先备份",
                tool_name="backup_file",
                parameters={
                    "path": "/etc/pam.d/system-auth",
                    "backup_suffix": ".bak.auto_remediation",
                },
                depends_on=["ar_parse_1"],
            ),
            SkillStep(
                id="ar_fix_pam_2",
                name="修复 PAM 锁定策略",
                description="根据 OS 类型应用正确的 PAM 锁定策略",
                tool_name="patch_pam_lockout_policy",
                parameters={},
                depends_on=["ar_fix_pam_1", "ar_env_2"],
            ),
            SkillStep(
                id="ar_fix_pam_3",
                name="验证 PAM 锁定策略",
                description="验证 PAM 锁定策略是否生效",
                tool_name="verify_pam_lockout_policy",
                parameters={},
                depends_on=["ar_fix_pam_2"],
            ),
            SkillStep(
                id="ar_fix_ssh_1",
                name="备份 SSH 配置",
                description="修改 SSH 配置前先备份",
                tool_name="backup_file",
                parameters={
                    "path": "/etc/ssh/sshd_config",
                    "backup_suffix": ".bak.auto_remediation",
                },
                depends_on=["ar_parse_1"],
            ),
            SkillStep(
                id="ar_fix_ssh_2",
                name="修复 SSH 配置",
                description="修复 SSH 安全配置（禁用 root 登录、密码认证等）",
                tool_name="patch_sshd_config",
                parameters={},
                depends_on=["ar_fix_ssh_1", "ar_env_1"],
            ),
            SkillStep(
                id="ar_fix_ssh_3",
                name="验证 SSH 配置",
                description="验证 SSH 配置正确性并 reload 服务",
                tool_name="verify_sshd_config",
                parameters={},
                depends_on=["ar_fix_ssh_2"],
            ),
            # 阶段4: 防火墙修复
            SkillStep(
                id="ar_fix_fw_1",
                name="检测防火墙类型",
                description="识别当前使用的防火墙类型",
                tool_name="detect_firewall_type",
                parameters={},
                depends_on=["ar_env_1"],
            ),
            SkillStep(
                id="ar_fix_fw_2",
                name="修复防火墙规则",
                description="根据防火墙类型应用正确的规则",
                tool_name="patch_firewall_rules",
                parameters={},
                depends_on=["ar_fix_fw_1", "ar_parse_1"],
            ),
            SkillStep(
                id="ar_fix_fw_3",
                name="验证防火墙规则",
                description="验证防火墙规则是否生效",
                tool_name="verify_firewall_rules",
                parameters={},
                depends_on=["ar_fix_fw_2"],
            ),
            # 阶段5: 用户/权限修复
            SkillStep(
                id="ar_fix_user_1",
                name="修复用户权限问题",
                description="修复检测到的用户权限问题",
                tool_name="patch_user_permissions",
                parameters={},
                depends_on=["ar_parse_1", "ar_env_3"],
            ),
            # 阶段6: 服务修复
            SkillStep(
                id="ar_fix_service_1",
                name="重启关键服务",
                description="安全地重启需要刷新配置的服务",
                tool_name="restart_service_safely",
                parameters={},
                depends_on=["ar_fix_ssh_3", "ar_fix_fw_3"],
            ),
            # 阶段7: 最终验证
            SkillStep(
                id="ar_verify_1",
                name="最终验证",
                description="验证所有修复项是否生效",
                tool_name="verify_all_fixes",
                parameters={},
                depends_on=[
                    "ar_fix_pam_3",
                    "ar_fix_ssh_3",
                    "ar_fix_fw_3",
                    "ar_fix_user_1",
                    "ar_fix_service_1",
                ],
            ),
        ]

    @property
    def required_context_keys(self) -> List[str]:
        return ["ssh_manager", "detection_report", "findings"]

    @property
    def output_template(self) -> str:
        return """# 自动修复报告

## 环境信息
{environment_info}

## 修复结果
{remediation_results}

## 已修复项
{fixed_items}

## 未修复项
{unfixed_items}

## 需要人工介入项
{blocked_items}

## 建议
{recommendations}
"""


def register_auto_remediation_skill(registry) -> None:
    """注册自动修复 skill"""
    registry.register(AutoRemediationSkill())


def get_auto_remediation_skill():
    """获取自动修复 skill 实例"""
    return AutoRemediationSkill()
