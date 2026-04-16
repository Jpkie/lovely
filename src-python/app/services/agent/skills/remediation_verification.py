"""修复验证 Skill - 验证修复是否真正生效

职责：
  - 对已经执行过修复的问题重新跑对应检测
  - 验证修复是否真正生效
  - 产出 before/after 对比
  - 给 Agent 最终报告提供 evidence

验证映射：
  - SSH 配置问题 → detect_ssh_audit
  - 防火墙问题 → detect_firewall
  - PAM/密码策略 → detect_user_audit
  - 文件权限 → detect_file_permission
  - 端口安全 → detect_port_scan
  - 进程安全 → detect_process

状态语义：
  - completed: 所有项验证通过
  - partially_completed: 部分验证通过
  - failed: 验证失败（修复未生效）
  - unknown: 无法验证（如工具不可用）
"""

from typing import Any, Dict, List

from ..skills.registry import BaseSkill, SkillStep


class RemediationVerificationSkill(BaseSkill):
    """修复验证 Skill"""

    @property
    def name(self) -> str:
        return "remediation_verification"

    @property
    def description(self) -> str:
        return (
            "验证安全修复是否真正生效，重新执行对应检测并对比前后状态，"
            "输出验证结果和 before/after 证据。"
        )

    @property
    def category(self) -> str:
        return "verification"

    @property
    def steps(self) -> List[SkillStep]:
        return [
            # ========== 阶段1: 收集修复前的检测结果 ==========
            SkillStep(
                id="rv_collect_before",
                name="收集修复前状态",
                description="从上下文中提取修复前的检测结果作为基准",
                tool_name="get_remediation_baseline",
                parameters={},
                depends_on=[],
            ),
            # ========== 阶段2: 按类型重新检测 ==========
            # SSH 配置验证
            SkillStep(
                id="rv_ssh_check",
                name="重新检测 SSH 配置",
                description="重新执行 SSH 审计检测当前配置状态",
                tool_name="detect_ssh_audit",
                parameters={},
                depends_on=["rv_collect_before"],
            ),
            # PAM/用户验证
            SkillStep(
                id="rv_user_check",
                name="重新检测用户安全",
                description="重新执行用户审计检测账户安全状态",
                tool_name="detect_user_audit",
                parameters={},
                depends_on=["rv_collect_before"],
            ),
            # 防火墙验证
            SkillStep(
                id="rv_fw_check",
                name="重新检测防火墙",
                description="重新执行防火墙检测当前规则状态",
                tool_name="detect_firewall",
                parameters={},
                depends_on=["rv_collect_before"],
            ),
            # 文件权限验证
            SkillStep(
                id="rv_file_check",
                name="重新检测文件权限",
                description="重新执行文件权限检测敏感文件安全状态",
                tool_name="detect_file_permission",
                parameters={},
                depends_on=["rv_collect_before"],
            ),
            # 端口安全验证
            SkillStep(
                id="rv_port_check",
                name="重新检测端口安全",
                description="重新执行端口扫描检测开放端口状态",
                tool_name="detect_port_scan",
                parameters={},
                depends_on=["rv_collect_before"],
            ),
            # 进程安全验证
            SkillStep(
                id="rv_process_check",
                name="重新检测进程安全",
                description="重新执行进程分析检测异常进程",
                tool_name="detect_process",
                parameters={},
                depends_on=["rv_collect_before"],
            ),
            # ========== 阶段3: 对比前后结果 ==========
            SkillStep(
                id="rv_compare",
                name="对比修复前后",
                description="对比修复前后的检测结果，生成差异报告",
                tool_name="compare_remediation_results",
                parameters={},
                depends_on=[
                    "rv_ssh_check",
                    "rv_user_check",
                    "rv_fw_check",
                    "rv_file_check",
                    "rv_port_check",
                    "rv_process_check",
                ],
            ),
            # ========== 阶段4: 生成验证报告 ==========
            SkillStep(
                id="rv_report",
                name="生成验证报告",
                description="汇总所有验证结果，生成最终验证报告",
                tool_name="generate_verification_report",
                parameters={},
                depends_on=["rv_compare"],
            ),
        ]

    @property
    def required_context_keys(self) -> List[str]:
        return [
            "ssh_manager",
            "remediation_results",
            "original_findings",
            "fixed_items",
            "unfixed_items",
        ]

    @property
    def output_template(self) -> str:
        return """# 修复验证报告

## 验证概要
{verification_summary}

## SSH 配置验证
{before_ssh}
{after_ssh}
## 结果: {ssh_verified}

## 用户安全验证
{before_user}
{after_user}
## 结果: {user_verified}

## 防火墙验证
{before_firewall}
{after_firewall}
## 结果: {firewall_verified}

## 文件权限验证
{before_file}
{after_file}
## 结果: {file_verified}

## 总体结论
{overall_result}

## 证据
{evidence}
"""


def register_remediation_verification_skill(registry) -> None:
    """注册修复验证 skill"""
    registry.register(RemediationVerificationSkill())


def get_remediation_verification_skill():
    """获取修复验证 skill 实例"""
    return RemediationVerificationSkill()
