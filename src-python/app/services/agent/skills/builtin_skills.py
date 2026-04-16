"""内置 Skills 实现"""

from typing import List

from .registry import BaseSkill, SkillStep


class HostTriageSkill(BaseSkill):
    """主机 triage skill - 主机安全状态快速评估"""

    @property
    def name(self) -> str:
        return "host_triage"

    @property
    def description(self) -> str:
        return (
            "对主机进行快速安全状态评估，检测开放端口、用户配置、进程异常和系统安全设置"
        )

    @property
    def category(self) -> str:
        return "triage"

    @property
    def steps(self) -> List[SkillStep]:
        return [
            SkillStep(
                id="ht_1",
                name="端口扫描",
                description="扫描主机开放端口",
                tool_name="detect_port_scan",
                parameters={},
            ),
            SkillStep(
                id="ht_2",
                name="用户审计",
                description="审计系统用户",
                tool_name="detect_user_audit",
                parameters={},
            ),
            SkillStep(
                id="ht_3",
                name="进程分析",
                description="分析运行进程",
                tool_name="detect_process",
                parameters={},
            ),
            SkillStep(
                id="ht_4",
                name="防火墙检查",
                description="检查防火墙状态",
                tool_name="detect_firewall",
                parameters={},
            ),
            SkillStep(
                id="ht_5",
                name="系统信息",
                description="获取系统基本信息",
                tool_name="uname",
                parameters={"all": True},
            ),
        ]

    @property
    def required_context_keys(self) -> List[str]:
        return ["ssh_manager"]

    @property
    def output_template(self) -> str:
        return """# 主机安全 triage 报告

## 系统概览
{system_info}

## 端口扫描结果
{port_scan}

## 用户审计结果
{user_audit}

## 进程分析结果
{process_analysis}

## 防火墙状态
{firewall}

## 风险评估
{risk_level}: {summary}
"""


class LogInvestigationSkill(BaseSkill):
    """日志调查 skill - 深入分析系统日志"""

    @property
    def name(self) -> str:
        return "log_investigation"

    @property
    def description(self) -> str:
        return "调查系统日志，发现认证失败、异常行为和安全事件"

    @property
    def category(self) -> str:
        return "investigation"

    @property
    def steps(self) -> List[SkillStep]:
        return [
            SkillStep(
                id="li_1",
                name="获取日志文件列表",
                description="列出可用日志文件",
                tool_name="list_log_files",
                parameters={},
            ),
            SkillStep(
                id="li_2",
                name="读取认证日志",
                description="读取系统认证日志",
                tool_name="read_system_log",
                parameters={"log_path": "/var/log/auth.log"},
            ),
            SkillStep(
                id="li_3",
                name="读取系统日志",
                description="读取系统主日志",
                tool_name="read_system_log",
                parameters={"log_path": "/var/log/syslog"},
            ),
            SkillStep(
                id="li_4",
                name="日志分析检测",
                description="执行日志分析检测",
                tool_name="detect_log",
                parameters={},
            ),
            SkillStep(
                id="li_5",
                name="读取 journal 日志",
                description="读取 systemd journal",
                tool_name="read_journalctl_log",
                parameters={"page_size": 50},
            ),
        ]

    @property
    def required_context_keys(self) -> List[str]:
        return ["ssh_manager"]

    @property
    def output_template(self) -> str:
        return """# 日志调查报告

## 日志分析结果
{log_analysis}

## 认证日志摘要
{auth_log}

## 系统日志摘要
{syslog}

## journal 日志摘要
{journal}

## 安全事件
{security_events}: {event_count} 条记录

## 建议
{recommendations}
"""


class ProcessHuntSkill(BaseSkill):
    """进程狩猎 skill - 查找可疑进程"""

    @property
    def name(self) -> str:
        return "process_hunt"

    @property
    def description(self) -> str:
        return "深入分析系统进程，发现可疑进程和高资源占用进程"

    @property
    def category(self) -> str:
        return "investigation"

    @property
    def steps(self) -> List[SkillStep]:
        return [
            SkillStep(
                id="ph_1",
                name="进程分析",
                description="执行进程分析",
                tool_name="detect_process",
                parameters={},
            ),
            SkillStep(
                id="ph_2",
                name="获取进程列表",
                description="获取详细进程列表",
                tool_name="process_list",
                parameters={"top": 50, "sort_by": "cpu"},
            ),
            SkillStep(
                id="ph_3",
                name="内存信息",
                description="获取内存使用情况",
                tool_name="memory_info",
                parameters={},
            ),
        ]

    @property
    def required_context_keys(self) -> List[str]:
        return ["ssh_manager"]

    @property
    def output_template(self) -> str:
        return """# 进程调查报告

## 进程分析结果
{process_analysis}

## 可疑进程
{suspicious_processes}

## 高资源进程
{high_resource_processes}

## 内存状态
{memory_info}

## 建议
{recommendations}
"""


class PortHuntSkill(BaseSkill):
    """端口狩猎 skill - 扫描和分析开放端口"""

    @property
    def name(self) -> str:
        return "port_hunt"

    @property
    def description(self) -> str:
        return "扫描主机开放端口，识别服务并检测潜在安全风险"

    @property
    def category(self) -> str:
        return "investigation"

    @property
    def steps(self) -> List[SkillStep]:
        return [
            SkillStep(
                id="poh_1",
                name="端口扫描",
                description="扫描开放端口",
                tool_name="detect_port_scan",
                parameters={},
            ),
            SkillStep(
                id="poh_2",
                name="网络连接",
                description="查看网络连接",
                tool_name="network_info",
                parameters={},
            ),
            SkillStep(
                id="poh_3",
                name="防火墙检查",
                description="检查防火墙规则",
                tool_name="detect_firewall",
                parameters={},
            ),
        ]

    @property
    def required_context_keys(self) -> List[str]:
        return ["ssh_manager"]

    @property
    def output_template(self) -> str:
        return """# 端口调查报告

## 开放端口
{open_ports}

## 网络接口
{network_info}

## 防火墙状态
{firewall_status}

## 高风险端口
{risky_ports}

## 建议
{recommendations}
"""


class SSHAuditSkill(BaseSkill):
    """SSH 审计 skill - SSH 安全配置审计"""

    @property
    def name(self) -> str:
        return "ssh_audit"

    @property
    def description(self) -> str:
        return "审计 SSH 服务配置安全性，检查认证方式和访问控制"

    @property
    def category(self) -> str:
        return "audit"

    @property
    def steps(self) -> List[SkillStep]:
        return [
            SkillStep(
                id="ssh_1",
                name="SSH 配置审计",
                description="审计 SSH 配置",
                tool_name="detect_ssh_audit",
                parameters={},
            ),
            SkillStep(
                id="ssh_2",
                name="用户审计",
                description="检查用户配置",
                tool_name="detect_user_audit",
                parameters={},
            ),
            SkillStep(
                id="ssh_3",
                name="文件权限检查",
                description="检查 SSH 相关文件权限",
                tool_name="detect_file_permission",
                parameters={},
            ),
            SkillStep(
                id="ssh_4",
                name="检查 sudo 配置",
                description="审计 sudo 权限",
                tool_name="run_whitelisted_command",
                parameters={"command_key": "sudoers"},
            ),
        ]

    @property
    def required_context_keys(self) -> List[str]:
        return ["ssh_manager"]

    @property
    def output_template(self) -> str:
        return """# SSH 安全审计报告

## SSH 配置审计
{ssh_config}

## 配置问题
{config_issues}

## 用户审计
{user_audit}

## 文件权限
{file_permissions}

## Sudo 权限
{sudo_config}

## 风险等级
{risk_level}

## 建议
{recommendations}
"""


class FixAdvisorSkill(BaseSkill):
    """修复建议 skill - 基于检测结果提供修复建议"""

    @property
    def name(self) -> str:
        return "fix_advisor"

    @property
    def description(self) -> str:
        return "基于安全检测结果，提供具体的修复建议和操作指南"

    @property
    def category(self) -> str:
        return "remediation"

    @property
    def steps(self) -> List[SkillStep]:
        return [
            SkillStep(
                id="fa_1",
                name="获取系统信息",
                description="收集系统信息",
                tool_name="hostname",
                parameters={},
            ),
            SkillStep(
                id="fa_2",
                name="获取运行时间",
                description="获取系统运行时间",
                tool_name="uptime",
                parameters={},
            ),
        ]

    @property
    def required_context_keys(self) -> List[str]:
        return ["ssh_manager", "detection_results"]

    @property
    def output_template(self) -> str:
        return """# 安全修复建议报告

## 系统信息
Hostname: {hostname}
运行时间: {uptime}

## 检测结果摘要
{detections_summary}

## 高风险问题
{high_risk_issues}

## 修复步骤

### 1. 紧急修复（高风险）
{urgent_fixes}

### 2. 标准修复（中风险）
{standard_fixes}

### 3. 最佳实践（建议）
{best_practices}

## 验证步骤
{verification_steps}

## 参考链接
{references}
"""


def register_builtin_skills(registry) -> None:
    """注册所有内置 skills"""
    from .auto_remediation import register_auto_remediation_skill
    from .remediation_verification import register_remediation_verification_skill
    from .capability_check import register_capability_check_skill
    from .safe_config_patch import register_safe_config_patch_skill
    from .hardening_baseline import register_hardening_baseline_skill
    from .incident_timeline import register_incident_timeline_skill

    registry.register(HostTriageSkill())
    registry.register(LogInvestigationSkill())
    registry.register(ProcessHuntSkill())
    registry.register(PortHuntSkill())
    registry.register(SSHAuditSkill())
    registry.register(FixAdvisorSkill())
    register_auto_remediation_skill(registry)
    register_remediation_verification_skill(registry)
    register_capability_check_skill(registry)
    register_safe_config_patch_skill(registry)
    register_hardening_baseline_skill(registry)
    register_incident_timeline_skill(registry)


def get_default_skill_registry():
    """获取默认的 skill 注册表"""
    from .registry import SkillRegistry

    registry = SkillRegistry()
    register_builtin_skills(registry)
    return registry
