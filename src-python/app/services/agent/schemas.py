"""Agent 服务 Schema 定义"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


class SkillType(str, Enum):
    """Skill 类型"""

    BASH = "bash"
    FILE = "file"
    SEARCH = "search"
    WEB = "web"
    SSH = "ssh"
    CUSTOM = "custom"


class SkillParameter(BaseModel):
    """Skill 参数定义"""

    name: str
    type: str = "string"
    description: str = ""
    required: bool = False
    default: Optional[Any] = None


class SkillDefinition(BaseModel):
    """Skill 定义"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    skill_type: SkillType = SkillType.CUSTOM
    parameters: List[SkillParameter] = Field(default_factory=list)
    command_template: str = ""
    enabled: bool = True


class ModelProvider(str, Enum):
    """模型提供商"""

    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    CLAUDE = "claude"
    CUSTOM = "custom"


class ModelRole(str, Enum):
    """模型角色"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ModelConfig(BaseModel):
    """模型配置"""

    provider: ModelProvider = ModelProvider.OPENAI
    model_name: str = "gpt-4"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 60
    fallback_model: Optional[str] = None


class RoleModelConfig(BaseModel):
    """角色模型配置"""

    planner: ModelConfig = Field(
        default_factory=lambda: ModelConfig(
            provider=ModelProvider.OPENAI, model_name="gpt-4"
        )
    )
    executor: ModelConfig = Field(
        default_factory=lambda: ModelConfig(
            provider=ModelProvider.OPENAI, model_name="gpt-4"
        )
    )
    summarizer: ModelConfig = Field(
        default_factory=lambda: ModelConfig(
            provider=ModelProvider.OPENAI, model_name="gpt-3.5-turbo"
        )
    )


class AgentRequest(BaseModel):
    """Agent 请求"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task: str
    context: Dict[str, Any] = Field(default_factory=dict)
    skills: List[str] = Field(default_factory=list)
    max_steps: int = 10
    timeout: int = 300
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PlanStep(BaseModel):
    """计划步骤"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    step_number: int
    description: str
    skill_id: Optional[str] = None
    tool_name: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Plan(BaseModel):
    """执行计划"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str
    steps: List[PlanStep] = Field(default_factory=list)
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ToolResult(BaseModel):
    """工具执行结果"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    output: Optional[str] = None
    error: Optional[str] = None
    exit_code: Optional[int] = None
    duration_ms: int = 0
    success: bool = True
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExecutionTrace(BaseModel):
    """执行轨迹"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: str
    step_id: str
    step_number: int
    tool_results: List[ToolResult] = Field(default_factory=list)
    status: str = "running"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class AgentResponse(BaseModel):
    """Agent 最终输出"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str
    plan_id: str
    execution_traces: List[ExecutionTrace] = Field(default_factory=list)
    final_output: Optional[str] = None
    error: Optional[str] = None
    status: str = "pending"
    total_steps: int = 0
    completed_steps: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class HostInfo(BaseModel):
    """主机信息摘要"""

    hostname: str = ""
    ip_address: str = ""
    os: str = ""
    os_version: str = ""
    kernel: str = ""
    architecture: str = ""
    uptime: str = ""
    cpu_count: int = 0
    memory_total: str = ""
    disk_total: str = ""
    network_interfaces: List[str] = Field(default_factory=list)


class PageInfo(BaseModel):
    """页面信息摘要"""

    title: str = ""
    url: str = ""
    content_type: str = ""
    size: int = 0
    status_code: int = 200
    headers: Dict[str, str] = Field(default_factory=dict)
    links: List[str] = Field(default_factory=list)
    forms: List[Dict[str, Any]] = Field(default_factory=list)


class HostSummaryContext(BaseModel):
    """主机摘要上下文"""

    host_info: HostInfo
    recent_commands: List[str] = Field(default_factory=list)
    suspicious_processes: List[Dict[str, Any]] = Field(default_factory=list)
    open_ports: List[int] = Field(default_factory=list)
    risk_level: str = "low"
    recommendations: List[str] = Field(default_factory=list)


class PageSummaryContext(BaseModel):
    """页面摘要上下文"""

    page_info: PageInfo
    content_summary: str = ""
    security_notes: List[str] = Field(default_factory=list)
    potential_threats: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class Message(BaseModel):
    """对话消息"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: ModelRole
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConversationHistory(BaseModel):
    """对话历史"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    messages: List[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LLMResponse(BaseModel):
    """LLM 响应"""

    content: str
    model: str
    provider: ModelProvider
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


class ToolCallRequest(BaseModel):
    """工具调用请求"""

    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ToolRegistry(BaseModel):
    """工具注册表"""

    tools: Dict[str, SkillDefinition] = Field(default_factory=dict)

    def register(self, skill: SkillDefinition) -> None:
        self.tools[skill.id] = skill

    def unregister(self, skill_id: str) -> None:
        if skill_id in self.tools:
            del self.tools[skill_id]

    def get(self, skill_id: str) -> Optional[SkillDefinition]:
        return self.tools.get(skill_id)

    def list_by_type(self, skill_type: SkillType) -> List[SkillDefinition]:
        return [s for s in self.tools.values() if s.skill_type == skill_type]


class AgentPlanStep(BaseModel):
    """Agent 计划步骤 (新版)"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    step_number: int
    description: str
    skill_id: Optional[str] = None
    skill_name: Optional[str] = None
    tool_name: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentExecutionTrace(BaseModel):
    """Agent 执行轨迹 (新版)"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: str
    step_id: str
    step_number: int
    tool_name: str
    tool_result_summary: Optional[str] = None
    output_preview: Optional[str] = None
    status: str = "running"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: int = 0
    success: bool = True
    error: Optional[str] = None


class AgentFinalResponse(BaseModel):
    """Agent 最终响应 (新版)"""

    summary: str
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    commands: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)


class AgentRunResponse(BaseModel):
    """Agent 运行响应 (完整结构)"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str
    task: str
    status: str
    skill_name: Optional[str] = None
    plan: Optional[Dict[str, Any]] = None
    traces: List[AgentExecutionTrace] = Field(default_factory=list)
    final: Optional[AgentFinalResponse] = None
    raw_summary: str = ""
    structured_output: Dict[str, Any] = Field(default_factory=dict)
    total_duration_ms: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
