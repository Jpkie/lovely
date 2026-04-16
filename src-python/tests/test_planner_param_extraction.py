"""Planner 参数提取测试 — ParamExtractor

覆盖:
  - log_investigation 参数提取 (source / log_path / page_size / keywords)
  - process_hunt 参数提取 (focus / top / sort_by / include_memory)
  - ssh_audit 参数提取 (config_path / check_config / check_users / check_permissions / check_sudo)
"""

import pytest
import sys
import os

# 确保可导入 app 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.agent.planner import ParamExtractor


# ────────────────── log_investigation ──────────────────


class TestLogInvestigationExtraction:
    """LogInvestigation 参数提取"""

    def test_default_system_source(self):
        """无特定关键词时，默认 source=system"""
        result = ParamExtractor.extract("调查系统日志", "log_investigation")
        # 无路径时 source 默认为 system
        assert result.get("source", "system") in ("system", None)

    def test_auth_keyword_sets_system_source(self):
        """提到 auth → source=system, log_path=/var/log/auth.log"""
        result = ParamExtractor.extract("调查 auth 日志中的异常", "log_investigation")
        assert result.get("source") == "system"
        assert result.get("log_path") == "/var/log/auth.log"

    def test_syslog_keyword_sets_system_source(self):
        """提到 syslog → source=system, log_path=/var/log/syslog"""
        result = ParamExtractor.extract("分析 syslog 日志", "log_investigation")
        assert result.get("source") == "system"
        assert result.get("log_path") == "/var/log/syslog"

    def test_journal_keyword_sets_journal_source(self):
        """提到 journal → source=journal"""
        result = ParamExtractor.extract("查看 journalctl 日志", "log_investigation")
        assert result.get("source") == "journal"

    def test_explicit_path_sets_custom_source(self):
        """提供显式路径 → source=custom"""
        result = ParamExtractor.extract("读取 /var/log/myapp.log", "log_investigation")
        assert result.get("source") == "custom"
        assert result.get("log_path") == "/var/log/myapp.log"

    def test_count_extraction_maps_to_page_size(self):
        """数量词映射到 page_size"""
        result = ParamExtractor.extract("查看最近 200 条 auth 日志", "log_investigation")
        assert result.get("page_size") == 200

    def test_keywords_extraction(self):
        """关键词提取 — '包含' 关键词格式"""
        result = ParamExtractor.extract("包含 failed,error 的日志", "log_investigation")
        assert "keywords" in result
        assert "failed" in result["keywords"]

    def test_page_size_capped_at_200(self):
        """page_size 上限为 200"""
        result = ParamExtractor.extract("查看最近 500 条日志", "log_investigation")
        assert result.get("page_size") == 200


# ────────────────── process_hunt ──────────────────


class TestProcessHuntExtraction:
    """ProcessHunt 参数提取"""

    def test_process_name_maps_to_focus(self):
        """进程名提取 → process_name"""
        result = ParamExtractor.extract("进程名 nginx", "process_hunt")
        assert result.get("process_name") == "nginx"

    def test_suspicious_keyword_maps_focus(self):
        """可疑关键词 → focus=suspicious"""
        result = ParamExtractor.extract("查找可疑进程", "process_hunt")
        assert result.get("focus") == "suspicious"

    def test_high_resource_maps_focus_and_sort(self):
        """高资源关键词 → focus=high_resource + sort_by=memory"""
        result = ParamExtractor.extract("查找高资源占用的进程", "process_hunt")
        assert result.get("focus") == "high_resource"
        assert result.get("sort_by") == "memory"

    def test_count_maps_to_top(self):
        """数量词映射到 top"""
        result = ParamExtractor.extract("查看前 50 个进程", "process_hunt")
        assert result.get("top") == 50

    def test_sort_by_cpu(self):
        """CPU 排序提取"""
        result = ParamExtractor.extract("按 CPU 排序查看进程", "process_hunt")
        assert result.get("sort_by") == "cpu"

    def test_sort_by_memory(self):
        """内存排序提取"""
        result = ParamExtractor.extract("按内存排序查看进程", "process_hunt")
        assert result.get("sort_by") == "memory"

    def test_include_memory_false(self):
        """不查内存 → include_memory=False"""
        result = ParamExtractor.extract("查找进程，不查内存", "process_hunt")
        assert result.get("include_memory") is False


# ────────────────── ssh_audit ──────────────────


class TestSSHAuditExtraction:
    """SSHAudit 参数提取"""

    def test_config_path_extraction(self):
        """SSH 配置路径提取 → config_path"""
        result = ParamExtractor.extract(
            "审计 SSH 配置 sshd_config /etc/ssh/sshd_config.d/custom.conf", "ssh_audit"
        )
        assert "config_path" in result

    def test_check_config_false(self):
        """不检查配置 → check_config=False"""
        result = ParamExtractor.extract("不检查配置，只审计用户", "ssh_audit")
        assert result.get("check_config") is False

    def test_check_config_true(self):
        """检查配置 → check_config=True"""
        result = ParamExtractor.extract("检查配置和用户", "ssh_audit")
        assert result.get("check_config") is True

    def test_check_users_false(self):
        """不检查用户 → check_users=False"""
        result = ParamExtractor.extract("不检查用户", "ssh_audit")
        assert result.get("check_users") is False

    def test_check_permissions_true(self):
        """检查权限 → check_permissions=True"""
        result = ParamExtractor.extract("检查文件权限", "ssh_audit")
        assert result.get("check_permissions") is True

    def test_check_sudo_false(self):
        """不检查 sudo → check_sudo=False"""
        result = ParamExtractor.extract("不检查 sudo", "ssh_audit")
        assert result.get("check_sudo") is False
