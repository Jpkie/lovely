"""上下文构建器 - 主机摘要与页面摘要"""

from typing import Any, Dict, List, Optional

from .schemas import (
    HostInfo,
    HostSummaryContext,
    PageInfo,
    PageSummaryContext,
)


class HostSummaryBuilder:
    """主机摘要构建器"""

    @staticmethod
    def build_basic_info(host_info: HostInfo) -> str:
        lines = [
            f"主机名: {host_info.hostname}",
            f"IP 地址: {host_info.ip_address}",
            f"操作系统: {host_info.os} {host_info.os_version}",
            f"内核版本: {host_info.kernel}",
            f"架构: {host_info.architecture}",
            f"运行时间: {host_info.uptime}",
            f"CPU 核心数: {host_info.cpu_count}",
            f"总内存: {host_info.memory_total}",
            f"总磁盘: {host_info.disk_total}",
        ]
        if host_info.network_interfaces:
            lines.append(f"网络接口: {', '.join(host_info.network_interfaces)}")
        return "\n".join(lines)

    @staticmethod
    def build_risk_assessment(context: HostSummaryContext) -> str:
        lines = [f"\n=== 风险评估 ==="]
        lines.append(f"风险等级: {context.risk_level.upper()}")

        if context.suspicious_processes:
            lines.append(f"\n可疑进程 ({len(context.suspicious_processes)}):")
            for proc in context.suspicious_processes[:5]:
                lines.append(
                    f"  - {proc.get('name', 'unknown')} (PID: {proc.get('pid', 'N/A')})"
                )

        if context.open_ports:
            lines.append(
                f"\n开放端口 ({len(context.open_ports)}): {', '.join(map(str, context.open_ports[:20]))}"
            )
            if len(context.open_ports) > 20:
                lines.append(f"  ... 还有 {len(context.open_ports) - 20} 个端口")

        return "\n".join(lines)

    @staticmethod
    def build_recommendations(context: HostSummaryContext) -> str:
        if not context.recommendations:
            return ""

        lines = ["\n=== 建议 ==="]
        for i, rec in enumerate(context.recommendations, 1):
            lines.append(f"{i}. {rec}")
        return "\n".join(lines)

    @classmethod
    def build_summary(cls, context: HostSummaryContext) -> str:
        parts = []

        parts.append("=== 主机基本信息 ===")
        parts.append(cls.build_basic_info(context.host_info))

        parts.append(cls.build_risk_assessment(context))

        if context.recent_commands:
            parts.append(f"\n=== 最近命令 ===")
            for cmd in context.recent_commands[-10:]:
                parts.append(f"  $ {cmd}")

        parts.append(cls.build_recommendations(context))

        return "\n".join(parts)

    @classmethod
    def build_prompt_context(cls, context: HostSummaryContext) -> Dict[str, Any]:
        return {
            "summary": cls.build_summary(context),
            "risk_level": context.risk_level,
            "suspicious_count": len(context.suspicious_processes),
            "open_port_count": len(context.open_ports),
            "recommendation_count": len(context.recommendations),
            "metadata": {
                "hostname": context.host_info.hostname,
                "os": context.host_info.os,
                "architecture": context.host_info.architecture,
            },
        }


class PageSummaryBuilder:
    """页面摘要构建器"""

    @staticmethod
    def build_basic_info(page_info: PageInfo) -> str:
        lines = [
            f"标题: {page_info.title}",
            f"URL: {page_info.url}",
            f"内容类型: {page_info.content_type}",
            f"大小: {page_info.size} bytes",
            f"状态码: {page_info.status_code}",
        ]
        return "\n".join(lines)

    @staticmethod
    def build_headers(page_info: PageInfo) -> str:
        if not page_info.headers:
            return "请求头: 无"

        lines = ["请求头:"]
        for key, value in page_info.headers.items():
            lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    @staticmethod
    def build_links(page_info: PageInfo) -> str:
        if not page_info.links:
            return "链接: 无"

        lines = [f"链接 ({len(page_info.links)}):"]
        for link in page_info.links[:10]:
            lines.append(f"  - {link}")
        if len(page_info.links) > 10:
            lines.append(f"  ... 还有 {len(page_info.links) - 10} 个链接")
        return "\n".join(lines)

    @staticmethod
    def build_forms(page_info: PageInfo) -> str:
        if not page_info.forms:
            return "表单: 无"

        lines = [f"表单 ({len(page_info.forms)}):"]
        for i, form in enumerate(page_info.forms[:5], 1):
            lines.append(f"  表单 {i}:")
            lines.append(f"    Action: {form.get('action', 'N/A')}")
            lines.append(f"    方法: {form.get('method', 'N/A')}")
            inputs = form.get("inputs", [])
            if inputs:
                lines.append(f"    输入字段: {', '.join(inputs)}")
        return "\n".join(lines)

    @staticmethod
    def build_security_analysis(context: PageSummaryContext) -> str:
        lines = ["\n=== 安全分析 ==="]

        if context.security_notes:
            lines.append("安全备注:")
            for note in context.security_notes:
                lines.append(f"  - {note}")

        if context.potential_threats:
            lines.append("\n潜在威胁:")
            for threat in context.potential_threats:
                lines.append(f"  ! {threat}")
        elif not context.security_notes:
            lines.append("未发现明显安全问题")

        return "\n".join(lines)

    @staticmethod
    def build_recommendations(context: PageSummaryContext) -> str:
        if not context.recommendations:
            return ""

        lines = ["\n=== 建议 ==="]
        for i, rec in enumerate(context.recommendations, 1):
            lines.append(f"{i}. {rec}")
        return "\n".join(lines)

    @classmethod
    def build_summary(cls, context: PageSummaryContext) -> str:
        parts = []

        parts.append("=== 页面基本信息 ===")
        parts.append(cls.build_basic_info(context.page_info))

        parts.append(cls.build_headers(context.page_info))
        parts.append(cls.build_links(context.page_info))
        parts.append(cls.build_forms(context.page_info))

        parts.append(cls.build_security_analysis(context))
        parts.append(cls.build_recommendations(context))

        return "\n".join(parts)

    @classmethod
    def build_prompt_context(cls, context: PageSummaryContext) -> Dict[str, Any]:
        return {
            "summary": cls.build_summary(context),
            "status_code": context.page_info.status_code,
            "link_count": len(context.page_info.links),
            "form_count": len(context.page_info.forms),
            "threat_count": len(context.potential_threats),
            "security_note_count": len(context.security_notes),
            "recommendation_count": len(context.recommendations),
            "metadata": {
                "title": context.page_info.title,
                "url": context.page_info.url,
                "content_type": context.page_info.content_type,
            },
        }


class ContextBuilderFactory:
    """上下文构建器工厂"""

    @staticmethod
    def create_host_builder() -> HostSummaryBuilder:
        return HostSummaryBuilder()

    @staticmethod
    def create_page_builder() -> PageSummaryBuilder:
        return PageSummaryBuilder()
