"""安全配置修补 Skill - 提供可控的配置修复能力

职责：
  - 提供可控的配置修复能力，不依赖 LLM 自由拼命令
  - 对高频配置项做结构化修补

适用场景：
  - SSH 配置修复
  - 防火墙启用/规则最小开放
  - 关键配置文件备份与替换
  - 文件权限修复
  - 服务 enable / restart / reload

要求：
  - 每次修改前自动备份
  - 修改后可做语法检查或状态验证
  - 失败时返回明确错误
  - 尽量避免 destructive command
"""

from typing import Any, Dict, List

from ..skills.registry import BaseSkill, SkillStep


class SafeConfigPatchSkill(BaseSkill):
    """安全配置修补 Skill"""

    @property
    def name(self) -> str:
        return "safe_config_patch"

    @property
    def description(self) -> str:
        return (
            "提供结构化的安全配置修复能力，支持 SSH/PAM/Firewall/User 等配置项的"
            "安全修改、备份、验证，防止修复过程中破坏系统。"
        )

    @property
    def category(self) -> str:
        return "remediation"

    @property
    def steps(self) -> List[SkillStep]:
        return [
            # ========== SSH 配置 ==========
            SkillStep(
                id="scp_ssh_backup",
                name="备份 SSH 配置",
                description="修改 SSH 配置前创建备份",
                tool_name="backup_file",
                parameters={
                    "path": "/etc/ssh/sshd_config",
                    "backup_suffix": ".bak.safe_patch",
                },
                depends_on=[],
            ),
            SkillStep(
                id="scp_ssh_patch",
                name="修补 SSH 配置",
                description="安全地修改 SSH 配置（禁用 root 登录、密码认证等）",
                tool_name="patch_sshd_config",
                parameters={},
                depends_on=["scp_ssh_backup"],
            ),
            SkillStep(
                id="scp_ssh_verify",
                name="验证 SSH 配置",
                description="验证 SSH 配置语法正确性",
                tool_name="verify_sshd_config",
                parameters={},
                depends_on=["scp_ssh_patch"],
            ),
            # ========== PAM 配置 ==========
            SkillStep(
                id="scp_pam_backup",
                name="备份 PAM 配置",
                description="修改 PAM 配置前创建备份",
                tool_name="backup_file",
                parameters={
                    "path": "/etc/pam.d/system-auth",
                    "backup_suffix": ".bak.safe_patch",
                },
                depends_on=[],
            ),
            SkillStep(
                id="scp_pam_patch",
                name="修补 PAM 配置",
                description="安全地修改 PAM 锁定策略",
                tool_name="patch_pam_lockout_policy",
                parameters={},
                depends_on=["scp_pam_backup"],
            ),
            SkillStep(
                id="scp_pam_verify",
                name="验证 PAM 配置",
                description="验证 PAM 配置是否正确应用",
                tool_name="verify_pam_lockout_policy",
                parameters={},
                depends_on=["scp_pam_patch"],
            ),
            # ========== 防火墙配置 ==========
            SkillStep(
                id="scp_fw_patch",
                name="修补防火墙规则",
                description="根据防火墙类型应用正确的规则",
                tool_name="patch_firewall_rules",
                parameters={},
                depends_on=[],
            ),
            SkillStep(
                id="scp_fw_verify",
                name="验证防火墙规则",
                description="验证防火墙规则是否生效",
                tool_name="verify_firewall_rules",
                parameters={},
                depends_on=["scp_fw_patch"],
            ),
            # ========== 用户权限配置 ==========
            SkillStep(
                id="scp_user_patch",
                name="修补用户权限",
                description="修复用户权限问题（锁定空密码账户等）",
                tool_name="patch_user_permissions",
                parameters={},
                depends_on=[],
            ),
            # ========== 服务刷新 ==========
            SkillStep(
                id="scp_service",
                name="刷新服务配置",
                description="安全地重启需要刷新配置的服务",
                tool_name="restart_service_safely",
                parameters={},
                depends_on=["scp_ssh_verify", "scp_fw_verify"],
            ),
        ]

    @property
    def required_context_keys(self) -> List[str]:
        return [
            "ssh_manager",
            "target_config",
            "env_info",
            "auto_remediation_mode",
        ]

    @property
    def output_template(self) -> str:
        return """# 安全配置修补报告

## 修改项
{modified_items}

## 备份项
{backed_up_items}

## 验证结果
{verification_results}

## 失败项（如有）
{failed_items}

## 建议
{recommendations}
"""

    def build_steps(self, args: Dict[str, Any], context: Dict[str, Any]) -> List[SkillStep]:
        """固定步骤模式：直接返回预定义的配置修补流程"""
        return self.steps


def register_safe_config_patch_skill(registry) -> None:
    """注册安全配置修补 skill"""
    registry.register(SafeConfigPatchSkill())


def get_safe_config_patch_skill():
    """获取安全配置修补 skill 实例"""
    return SafeConfigPatchSkill()
