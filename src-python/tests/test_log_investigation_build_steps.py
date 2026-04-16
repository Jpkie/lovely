"""LogInvestigationSkill.build_steps() 行为测试

覆盖 source 三种模式:
  - system: 读 auth.log + syslog + detect_log
  - journal: 仅读 journalctl + detect_log
  - custom: 仅读指定 log_path + detect_log
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.agent.skills.builtin_skills import LogInvestigationSkill


@pytest.fixture
def skill():
    return LogInvestigationSkill()


class TestLogInvestigationBuildSteps:
    """LogInvestigationSkill.build_steps() 三种 source 模式"""

    def test_system_source_reads_auth_and_syslog(self, skill):
        """source=system: 应包含 auth.log 和 syslog 读取步骤"""
        steps = skill.build_steps({"source": "system"}, {})

        tool_names = [s.tool_name for s in steps]
        assert "list_log_files" in tool_names
        assert "read_system_log" in tool_names
        assert "detect_log" in tool_names

        # 确认有 auth.log 和 syslog 两个 read_system_log 步骤
        log_reads = [s for s in steps if s.tool_name == "read_system_log"]
        log_paths = [s.parameters.get("log_path") for s in log_reads]
        assert "/var/log/auth.log" in log_paths
        assert "/var/log/syslog" in log_paths

        # 不应包含 journalctl 步骤
        assert "read_journalctl_log" not in tool_names

    def test_journal_source_only_reads_journal(self, skill):
        """source=journal: 应只包含 journalctl 步骤，不包含 auth.log/syslog"""
        steps = skill.build_steps({"source": "journal"}, {})

        tool_names = [s.tool_name for s in steps]
        assert "list_log_files" in tool_names
        assert "read_journalctl_log" in tool_names
        assert "detect_log" in tool_names

        # 不应包含 read_system_log
        assert "read_system_log" not in tool_names

    def test_custom_source_only_reads_specified_path(self, skill):
        """source=custom: 应只读取指定 log_path，不读 auth.log/syslog/journal"""
        steps = skill.build_steps({
            "source": "custom",
            "log_path": "/var/log/myapp.log",
        }, {})

        tool_names = [s.tool_name for s in steps]
        assert "list_log_files" in tool_names
        assert "read_system_log" in tool_names
        assert "detect_log" in tool_names

        # 唯一的 read_system_log 应使用指定路径
        log_reads = [s for s in steps if s.tool_name == "read_system_log"]
        assert len(log_reads) == 1
        assert log_reads[0].parameters.get("log_path") == "/var/log/myapp.log"

        # 不应包含 journalctl
        assert "read_journalctl_log" not in tool_names

    def test_default_args_equals_system(self, skill):
        """空参数等价于 source=system"""
        steps_default = skill.build_steps({}, {})
        steps_system = skill.build_steps({"source": "system"}, {})

        default_tools = [s.tool_name for s in steps_default]
        system_tools = [s.tool_name for s in steps_system]
        assert default_tools == system_tools

    def test_keywords_passed_to_detect(self, skill):
        """keywords 参数应传递给 detect_log 步骤"""
        steps = skill.build_steps({
            "source": "system",
            "keywords": ["failed", "denied"],
        }, {})

        detect_step = next(s for s in steps if s.tool_name == "detect_log")
        assert detect_step.parameters.get("keywords") == ["failed", "denied"]

    def test_page_size_passed_to_read_steps(self, skill):
        """page_size 参数应传递给读取步骤"""
        steps = skill.build_steps({
            "source": "system",
            "page_size": 50,
        }, {})

        read_steps = [s for s in steps if s.tool_name == "read_system_log"]
        for rs in read_steps:
            assert rs.parameters.get("page_size") == 50

    def test_system_no_journal_step(self, skill):
        """system 模式不应无条件追加 journalctl 步骤"""
        steps = skill.build_steps({"source": "system"}, {})
        tool_names = [s.tool_name for s in steps]
        assert "read_journalctl_log" not in tool_names
