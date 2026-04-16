"""内置 Skills 实现"""

from typing import Any, Dict, List

from .registry import BaseSkill, SkillStep
from ..schemas import SkillParameter


# ── 以下 3 个 Skill 改造为参数化模式：支持 build_steps(args, context) 动态生成步骤 ──


class LogInvestigationSkill(BaseSkill):
    """日志调查 skill - 深入分析系统日志（参数化版本）"""

    @property
    def name(self) -> str:
        return "log_investigation"

    @property
    def description(self) -> str:
        return "调查系统日志，发现认证失败、异常行为和安全事件"

    @property
    def category(self) -> str:
        return "investigation"

    # ── 参数定义 ──
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="source",
                type="string",
                description="日志来源: system(读取 auth.log+syslog) / journal(仅 journalctl) / custom(仅指定 log_path)",
                required=False,
                default="system",
            ),
            SkillParameter(
                name="log_path",
                type="string",
                description="自定义日志文件路径（source=custom 时生效）",
                required=False,
                default="/var/log/auth.log",
            ),
            SkillParameter(
                name="keywords",
                type="list",
                description="在日志中搜索的关键词列表（如 failed, error, denied）",
                required=False,
                default=None,
            ),
            SkillParameter(
                name="page_size",
                type="integer",
                description="单页读取日志的行数上限",
                required=False,
                default=100,
            ),
        ]

    @property
    def steps(self) -> List[SkillStep]:
        """默认固定步骤（无参时使用，等同于 source=system）"""
        return [
            SkillStep(id="li_1", name="获取日志文件列表", description="列出可用日志文件", tool_name="list_log_files", parameters={}),
            SkillStep(id="li_2", name="读取认证日志", description="读取系统认证日志", tool_name="read_system_log", parameters={"log_path": "/var/log/auth.log"}),
            SkillStep(id="li_3", name="读取系统日志", description="读取系统主日志", tool_name="read_system_log", parameters={"log_path": "/var/log/syslog"}),
            SkillStep(id="li_4", name="日志分析检测", description="执行日志分析检测", tool_name="detect_log", parameters={}),
        ]

    def build_steps(self, args: Dict[str, Any], context: Dict[str, Any]) -> List[SkillStep]:
        """根据 args 动态构建日志调查步骤

        source 分支逻辑:
          - system:  读 auth.log + syslog + 日志分析检测
          - journal: 仅读 journalctl + 日志分析检测
          - custom:  仅读指定 log_path + 日志分析检测
        """
        source = args.get("source", "system")
        log_path = args.get("log_path", "/var/log/auth.log")
        page_size = args.get("page_size", 100)
        keywords = args.get("keywords")

        dynamic_steps = [
            SkillStep(id="li_1", name="获取日志文件列表", description="列出可用日志文件", tool_name="list_log_files", parameters={}),
        ]

        # ── 按 source 分支：每种来源只生成对应的读取步骤 ──
        if source == "journal":
            # journal 模式：仅读 journalctl，不读 auth.log / syslog
            dynamic_steps.append(SkillStep(
                id="li_2", name="读取 journal 日志",
                description="读取 systemd journal",
                tool_name="read_journalctl_log",
                parameters={"page_size": min(page_size, 200)},
            ))
        elif source == "custom":
            # 自定义模式：仅读取指定路径的日志
            dynamic_steps.append(SkillStep(
                id="li_2", name=f"读取自定义日志 ({log_path})",
                description=f"读取指定日志文件: {log_path}",
                tool_name="read_system_log",
                parameters={"log_path": log_path, "page_size": page_size},
            ))
        else:
            # system 模式（默认）：读 auth.log + syslog
            dynamic_steps.append(SkillStep(
                id="li_2", name="读取认证日志",
                description="读取系统认证日志 /var/log/auth.log",
                tool_name="read_system_log",
                parameters={"log_path": "/var/log/auth.log", "page_size": page_size},
            ))
            dynamic_steps.append(SkillStep(
                id="li_3", name="读取系统日志",
                description="读取系统主日志 /var/log/syslog",
                tool_name="read_system_log",
                parameters={"log_path": "/var/log/syslog", "page_size": page_size},
            ))

        # 日志分析检测（所有来源都需要）
        detect_params: Dict[str, Any] = {}
        if keywords:
            detect_params["keywords"] = keywords
        dynamic_steps.append(SkillStep(
            id="li_4", name="日志分析检测",
            description="执行日志分析检测（含关键词过滤）",
            tool_name="detect_log",
            parameters=detect_params,
        ))

        return dynamic_steps

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
    """进程狩猎 skill - 查找可疑进程（参数化版本）"""

    @property
    def name(self) -> str:
        return "process_hunt"

    @property
    def description(self) -> str:
        return "深入分析系统进程，发现可疑进程和高资源占用进程"

    @property
    def category(self) -> str:
        return "investigation"

    # ── 参数定义（按要求更新） ──
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="top",
                type="integer",
                description="返回前 N 个高资源占用进程",
                required=False,
                default=50,
            ),
            SkillParameter(
                name="sort_by",
                type="string",
                description="排序字段 (cpu / memory)",
                required=False,
                default="cpu",
            ),
            SkillParameter(
                name="focus",
                type="string",
                description="调查焦点：all（所有进程）、suspicious（仅可疑进程）、high_resource（仅高资源进程）",
                required=False,
                default="all",
            ),
            SkillParameter(
                name="process_name",
                type="string",
                description="目标进程名，用于定向查找指定进程",
                required=False,
                default="",
            ),
            SkillParameter(
                name="include_memory",
                type="boolean",
                description="是否包含系统内存信息检查",
                required=False,
                default=True,
            ),
        ]

    @property
    def steps(self) -> List[SkillStep]:
        """默认固定步骤"""
        return [
            SkillStep(id="ph_1", name="进程分析", description="执行进程分析", tool_name="detect_process", parameters={}),
            SkillStep(id="ph_2", name="获取进程列表", description="获取详细进程列表", tool_name="process_list", parameters={"top": 50, "sort_by": "cpu"}),
            SkillStep(id="ph_3", name="内存信息", description="获取内存使用情况", tool_name="memory_info", parameters={}),
        ]

    def build_steps(self, args: Dict[str, Any], context: Dict[str, Any]) -> List[SkillStep]:
        """根据 args 动态构建进程调查步骤"""
        top = args.get("top", 50)
        sort_by = args.get("sort_by", "cpu")
        focus = args.get("focus", "all")
        process_name = args.get("process_name", "")
        include_memory = args.get("include_memory", True)

        dynamic_steps = []

        # 基础进程检测
        detect_params = {"focus": focus}
        if process_name:
            detect_params["process_name"] = process_name
        dynamic_steps.append(SkillStep(
            id="ph_1", name="进程分析",
            description=f"进程分析（焦点: {focus}）" + (f"，目标进程: {process_name}" if process_name else ""),
            tool_name="detect_process",
            parameters=detect_params,
        ))

        # 进程列表 + 排序
        list_params = {"top": top, "sort_by": sort_by}
        if process_name:
            list_params["process_name"] = process_name
        dynamic_steps.append(SkillStep(
            id="ph_2", name="获取进程列表",
            description=f"获取前 {top} 个进程（按 {sort_by} 排序）" + (f"，筛选: {process_name}" if process_name else ""),
            tool_name="process_list",
            parameters=list_params,
        ))

        # 内存信息（可选）
        if include_memory:
            dynamic_steps.append(SkillStep(
                id="ph_3", name="内存信息", description="获取内存使用情况",
                tool_name="memory_info", parameters={},
            ))

        return dynamic_steps

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


class SSHAuditSkill(BaseSkill):
    """SSH 审计 skill - SSH 安全配置审计（参数化版本）"""

    @property
    def name(self) -> str:
        return "ssh_audit"

    @property
    def description(self) -> str:
        return "审计 SSH 服务配置安全性，检查认证方式和访问控制"

    @property
    def category(self) -> str:
        return "audit"

    # ── 参数定义（按要求更新） ──
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="check_config",
                type="boolean",
                description="是否检查 sshd_config 配置文件内容",
                required=False,
                default=True,
            ),
            SkillParameter(
                name="check_users",
                type="boolean",
                description="是否审计 SSH 用户配置",
                required=False,
                default=True,
            ),
            SkillParameter(
                name="check_permissions",
                type="boolean",
                description="是否检查 SSH 相关文件权限",
                required=False,
                default=True,
            ),
            SkillParameter(
                name="check_sudo",
                type="boolean",
                description="是否审计 sudo 权限配置",
                required=False,
                default=True,
            ),
            SkillParameter(
                name="config_path",
                type="string",
                description="SSH 配置文件路径（默认 /etc/ssh/sshd_config）",
                required=False,
                default="/etc/ssh/sshd_config",
            ),
        ]

    @property
    def steps(self) -> List[SkillStep]:
        """默认固定步骤"""
        return [
            SkillStep(id="ssh_1", name="SSH 配置审计", description="审计 SSH 配置", tool_name="detect_ssh_audit", parameters={}),
            SkillStep(id="ssh_2", name="用户审计", description="检查用户配置", tool_name="detect_user_audit", parameters={}),
            SkillStep(id="ssh_3", name="文件权限检查", description="检查 SSH 相关文件权限", tool_name="detect_file_permission", parameters={}),
            SkillStep(id="ssh_4", name="检查 sudo 配置", description="审计 sudo 权限", tool_name="run_whitelisted_command", parameters={"command_key": "sudoers"}),
        ]

    def build_steps(self, args: Dict[str, Any], context: Dict[str, Any]) -> List[SkillStep]:
        """根据 args 动态构建 SSH 审计步骤"""
        check_config = args.get("check_config", True)
        check_users = args.get("check_users", True)
        check_permissions = args.get("check_permissions", True)
        check_sudo = args.get("check_sudo", True)
        config_path = args.get("config_path", "/etc/ssh/sshd_config")

        dynamic_steps = []
        step_idx = 1

        if check_config:
            dynamic_steps.append(SkillStep(
                id=f"ssh_{step_idx}", name="SSH 配置审计",
                description=f"审计 SSH 服务配置文件: {config_path}",
                tool_name="detect_ssh_audit",
                parameters={"config_path": config_path},
            ))
            step_idx += 1

        if check_users:
            dynamic_steps.append(SkillStep(
                id=f"ssh_{step_idx}", name="用户审计",
                description="检查 SSH 用户配置和登录历史",
                tool_name="detect_user_audit",
                parameters={},
            ))
            step_idx += 1

        if check_permissions:
            dynamic_steps.append(SkillStep(
                id=f"ssh_{step_idx}", name="文件权限检查",
                description="检查 SSH 相关文件和目录权限",
                tool_name="detect_file_permission",
                parameters={},
            ))
            step_idx += 1

        if check_sudo:
            dynamic_steps.append(SkillStep(
                id=f"ssh_{step_idx}", name="检查 sudo 配置",
                description="审计 sudo 权限配置",
                tool_name="run_whitelisted_command",
                parameters={"command_key": "sudoers"},
            ))

        return dynamic_steps

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


# ── 以下保持原样未改动的 Skills ──


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

    # ── 参数定义 ──
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="skip_port_scan",
                type="boolean",
                description="是否跳过端口扫描步骤",
                required=False,
                default=False,
            ),
            SkillParameter(
                name="skip_user_audit",
                type="boolean",
                description="是否跳过用户审计步骤",
                required=False,
                default=False,
            ),
            SkillParameter(
                name="skip_process_analysis",
                type="boolean",
                description="是否跳过程序分析步骤",
                required=False,
                default=False,
            ),
            SkillParameter(
                name="skip_firewall_check",
                type="boolean",
                description="是否跳过防火墙检查步骤",
                required=False,
                default=False,
            ),
            SkillParameter(
                name="skip_system_info",
                type="boolean",
                description="是否跳过系统信息获取步骤",
                required=False,
                default=False,
            ),
            SkillParameter(
                name="port_range",
                type="string",
                description="端口扫描范围，例如 1-1000、常用端口、全端口",
                required=False,
                default="常用端口",
            ),
        ]

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

    def build_steps(self, args: Dict[str, Any], context: Dict[str, Any]) -> List[SkillStep]:
        """根据参数动态生成主机评估步骤"""
        skip_port_scan = args.get("skip_port_scan", False)
        skip_user_audit = args.get("skip_user_audit", False)
        skip_process_analysis = args.get("skip_process_analysis", False)
        skip_firewall_check = args.get("skip_firewall_check", False)
        skip_system_info = args.get("skip_system_info", False)
        port_range = args.get("port_range", "常用端口")

        dynamic_steps = []
        step_idx = 1

        if not skip_port_scan:
            dynamic_steps.append(SkillStep(
                id=f"ht_{step_idx}",
                name="端口扫描",
                description=f"扫描主机开放端口（范围：{port_range}）",
                tool_name="detect_port_scan",
                parameters={"port_range": port_range},
            ))
            step_idx += 1

        if not skip_user_audit:
            dynamic_steps.append(SkillStep(
                id=f"ht_{step_idx}",
                name="用户审计",
                description="审计系统用户",
                tool_name="detect_user_audit",
                parameters={},
            ))
            step_idx += 1

        if not skip_process_analysis:
            dynamic_steps.append(SkillStep(
                id=f"ht_{step_idx}",
                name="进程分析",
                description="分析运行进程",
                tool_name="detect_process",
                parameters={},
            ))
            step_idx += 1

        if not skip_firewall_check:
            dynamic_steps.append(SkillStep(
                id=f"ht_{step_idx}",
                name="防火墙检查",
                description="检查防火墙状态",
                tool_name="detect_firewall",
                parameters={},
            ))
            step_idx += 1

        if not skip_system_info:
            dynamic_steps.append(SkillStep(
                id=f"ht_{step_idx}",
                name="系统信息",
                description="获取系统基本信息",
                tool_name="uname",
                parameters={"all": True},
            ))

        return dynamic_steps

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

    # ── 参数定义 ──
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="port_range",
                type="string",
                description="端口扫描范围，例如 1-1000、常用端口、全端口",
                required=False,
                default="常用端口",
            ),
            SkillParameter(
                name="include_network",
                type="boolean",
                description="是否包含网络连接检查步骤",
                required=False,
                default=True,
            ),
            SkillParameter(
                name="include_firewall",
                type="boolean",
                description="是否包含防火墙检查步骤",
                required=False,
                default=True,
            ),
            SkillParameter(
                name="fast_scan",
                type="boolean",
                description="快速扫描模式（只扫描TOP 100常用端口）",
                required=False,
                default=False,
            ),
        ]

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

    def build_steps(self, args: Dict[str, Any], context: Dict[str, Any]) -> List[SkillStep]:
        """根据参数动态生成端口调查步骤"""
        port_range = args.get("port_range", "常用端口")
        include_network = args.get("include_network", True)
        include_firewall = args.get("include_firewall", True)
        fast_scan = args.get("fast_scan", False)

        # 快速扫描模式覆盖端口范围
        if fast_scan:
            port_range = "TOP 100常用端口"

        dynamic_steps = []
        step_idx = 1

        dynamic_steps.append(SkillStep(
            id=f"poh_{step_idx}",
            name="端口扫描",
            description=f"扫描开放端口（范围：{port_range}）",
            tool_name="detect_port_scan",
            parameters={"port_range": port_range, "fast_scan": fast_scan},
        ))
        step_idx += 1

        if include_network:
            dynamic_steps.append(SkillStep(
                id=f"poh_{step_idx}",
                name="网络连接",
                description="查看网络连接",
                tool_name="network_info",
                parameters={},
            ))
            step_idx += 1

        if include_firewall:
            dynamic_steps.append(SkillStep(
                id=f"poh_{step_idx}",
                name="防火墙检查",
                description="检查防火墙规则",
                tool_name="detect_firewall",
                parameters={},
            ))

        return dynamic_steps

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

    # ── 参数定义 ──
    @property
    def parameters(self) -> List[SkillParameter]:
        return [
            SkillParameter(
                name="include_urgent_fixes",
                type="boolean",
                description="是否包含紧急修复建议（高风险问题）",
                required=False,
                default=True,
            ),
            SkillParameter(
                name="include_standard_fixes",
                type="boolean",
                description="是否包含标准修复建议（中风险问题）",
                required=False,
                default=True,
            ),
            SkillParameter(
                name="include_best_practices",
                type="boolean",
                description="是否包含最佳实践建议",
                required=False,
                default=True,
            ),
            SkillParameter(
                name="include_verification_steps",
                type="boolean",
                description="是否包含修复后的验证步骤",
                required=False,
                default=True,
            ),
            SkillParameter(
                name="include_references",
                type="boolean",
                description="是否包含参考链接",
                required=False,
                default=True,
            ),
            SkillParameter(
                name="suggest_auto_remediation",
                type="boolean",
                description="是否建议可自动修复的方案",
                required=False,
                default=True,
            ),
        ]

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

    def build_steps(self, args: Dict[str, Any], context: Dict[str, Any]) -> List[SkillStep]:
        """根据参数动态生成修复建议步骤"""
        # 基础信息收集步骤始终执行
        dynamic_steps = [
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

        # 后续步骤生成逻辑由检测器根据参数决定输出内容，这里步骤固定但输出会根据参数调整
        return dynamic_steps

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
