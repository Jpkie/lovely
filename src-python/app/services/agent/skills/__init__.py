"""Skills 模块"""

from .registry import BaseSkill, SkillDefinition, SkillRegistry, SkillStep
from .builtin_skills import (
    HostTriageSkill,
    LogInvestigationSkill,
    ProcessHuntSkill,
    PortHuntSkill,
    SSHAuditSkill,
    FixAdvisorSkill,
    register_builtin_skills,
    get_default_skill_registry,
)
from .auto_remediation import (
    AutoRemediationSkill,
    register_auto_remediation_skill,
    get_auto_remediation_skill,
)
from .remediation_verification import (
    RemediationVerificationSkill,
    register_remediation_verification_skill,
    get_remediation_verification_skill,
)
from .capability_check import (
    CapabilityCheckSkill,
    register_capability_check_skill,
    get_capability_check_skill,
)
from .safe_config_patch import (
    SafeConfigPatchSkill,
    register_safe_config_patch_skill,
    get_safe_config_patch_skill,
)
from .hardening_baseline import (
    HardeningBaselineSkill,
    register_hardening_baseline_skill,
    get_hardening_baseline_skill,
)
from .incident_timeline import (
    IncidentTimelineSkill,
    register_incident_timeline_skill,
    get_incident_timeline_skill,
)

__all__ = [
    # Registry base
    "BaseSkill",
    "SkillDefinition",
    "SkillRegistry",
    "SkillStep",
    # Builtin skills
    "HostTriageSkill",
    "LogInvestigationSkill",
    "ProcessHuntSkill",
    "PortHuntSkill",
    "SSHAuditSkill",
    "FixAdvisorSkill",
    "register_builtin_skills",
    "get_default_skill_registry",
    # New skills
    "AutoRemediationSkill",
    "register_auto_remediation_skill",
    "get_auto_remediation_skill",
    "RemediationVerificationSkill",
    "register_remediation_verification_skill",
    "get_remediation_verification_skill",
    "CapabilityCheckSkill",
    "register_capability_check_skill",
    "get_capability_check_skill",
    "SafeConfigPatchSkill",
    "register_safe_config_patch_skill",
    "get_safe_config_patch_skill",
    "HardeningBaselineSkill",
    "register_hardening_baseline_skill",
    "get_hardening_baseline_skill",
    "IncidentTimelineSkill",
    "register_incident_timeline_skill",
    "get_incident_timeline_skill",
]
