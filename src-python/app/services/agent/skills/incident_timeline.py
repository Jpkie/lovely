"""事件时间线 Skill - 整合多源证据生成事件时间线

职责：
  - 把多源证据串起来，而不是只输出散点 findings
  - 整合来源：日志分析、最近登录、开放端口、可疑进程、cron/startup、SSH 配置、网络连接

输出：
  - 时间线
  - 可疑行为链
  - 风险归因
  - 建议下一步调查方向
"""

from typing import Any, Dict, List

from ..skills.registry import BaseSkill, SkillStep


class IncidentTimelineSkill(BaseSkill):
    """事件时间线 Skill"""

    @property
    def name(self) -> str:
        return "incident_timeline"

    @property
    def description(self) -> str:
        return (
            "整合多源安全证据（日志、登录、进程、网络连接、计划任务等），"
            "生成攻击时间线、可疑行为链、风险归因和后续调查建议。"
        )

    @property
    def category(self) -> str:
        return "investigation"

    @property
    def steps(self) -> List[SkillStep]:
        return [
            # ========== 证据收集阶段 ==========
            SkillStep(
                id="it_auth_logs",
                name="收集认证日志",
                description="收集系统认证日志（auth.log/syslog）中的失败登录和异常",
                tool_name="read_system_log",
                parameters={"log_path": "/var/log/auth.log"},
                depends_on=[],
            ),
            SkillStep(
                id="it_last_logins",
                name="收集最近登录",
                description="获取系统最近登录记录",
                tool_name="run_whitelisted_command",
                parameters={"command_key": "recent_logins"},
                depends_on=[],
            ),
            SkillStep(
                id="it_failed_logins",
                name="收集失败登录",
                description="获取失败登录尝试记录",
                tool_name="run_whitelisted_command",
                parameters={"command_key": "failed_logins"},
                depends_on=[],
            ),
            SkillStep(
                id="it_network",
                name="收集网络连接",
                description="获取当前网络连接和监听端口",
                tool_name="network_info",
                parameters={},
                depends_on=[],
            ),
            SkillStep(
                id="it_process",
                name="收集进程列表",
                description="获取系统进程列表，识别异常进程",
                tool_name="process_list",
                parameters={"top": 100, "sort_by": "cpu"},
                depends_on=[],
            ),
            SkillStep(
                id="it_cron",
                name="收集定时任务",
                description="获取用户和系统计划任务",
                tool_name="run_whitelisted_command",
                parameters={"command_key": "cron_jobs"},
                depends_on=[],
            ),
            SkillStep(
                id="it_system_crons",
                name="收集系统定时任务",
                description="获取系统级计划任务",
                tool_name="run_whitelisted_command",
                parameters={"command_key": "system_crons"},
                depends_on=[],
            ),
            SkillStep(
                id="it_ssh_keys",
                name="收集 SSH 密钥",
                description="检查 SSH authorized_keys 和 SSH 配置",
                tool_name="detect_ssh_audit",
                parameters={},
                depends_on=[],
            ),
            SkillStep(
                id="it_kernel",
                name="收集内核消息",
                description="获取内核日志（dmesg）中的异常",
                tool_name="run_whitelisted_command",
                parameters={"command_key": "kernel_messages"},
                depends_on=[],
            ),
            SkillStep(
                id="it_services",
                name="收集服务状态",
                description="获取运行中的服务和自启动服务",
                tool_name="run_whitelisted_command",
                parameters={"command_key": "systemd_services"},
                depends_on=[],
            ),
            # ========== 分析与关联阶段 ==========
            SkillStep(
                id="it_correlate",
                name="关联事件分析",
                description="关联时间、来源 IP、用户、进程等维度分析可疑行为",
                tool_name="correlate_security_events",
                parameters={},
                depends_on=[
                    "it_auth_logs",
                    "it_last_logins",
                    "it_failed_logins",
                    "it_network",
                    "it_process",
                    "it_cron",
                    "it_system_crons",
                    "it_ssh_keys",
                    "it_kernel",
                    "it_services",
                ],
            ),
            # ========== 生成报告阶段 ==========
            SkillStep(
                id="it_timeline",
                name="生成事件时间线",
                description="基于关联分析结果生成攻击时间线",
                tool_name="generate_incident_timeline",
                parameters={},
                depends_on=["it_correlate"],
            ),
            SkillStep(
                id="it_report",
                name="生成完整报告",
                description="生成包含时间线、风险归因、调查建议的完整报告",
                tool_name="generate_investigation_report",
                parameters={},
                depends_on=["it_timeline"],
            ),
        ]

    @property
    def required_context_keys(self) -> List[str]:
        return ["ssh_manager", "evidence_sources"]

    @property
    def output_template(self) -> str:
        return """# 安全事件调查报告

## 事件概要
{incident_summary}

## 时间线
{timeline}

## 可疑行为链
{suspicious_chains}

## 风险归因
{risk_attribution}

## 涉及指标
| 指标类型 | 详情 |
|----------|------|
| IP 地址 | {involved_ips} |
| 用户账户 | {involved_users} |
| 进程 | {involved_processes} |
| 文件 | {involved_files} |
| 端口 | {involved_ports} |

## 建议下一步调查
{next_steps}

## 证据摘要
{evidence_summary}
"""


def register_incident_timeline_skill(registry) -> None:
    """注册事件时间线 skill"""
    registry.register(IncidentTimelineSkill())


def get_incident_timeline_skill():
    """获取事件时间线 skill 实例"""
    return IncidentTimelineSkill()
