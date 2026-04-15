/**
 * Agent 类型定义
 * 与后端 schemas.py 对应
 */

// Agent 运行请求
export interface AgentRunRequest {
  task: string;
  skills?: string[];
  context?: Record<string, any>;
  max_steps?: number;
}

// Skill 定义
export interface SkillDefinition {
  id: string;
  name: string;
  description: string;
  category: string;
  step_count: number;
}

// Tool 定义
export interface ToolDefinition {
  id: string;
  name: string;
  description: string;
  skill_type?: string;
  enabled?: boolean;
}

// 主机信息
export interface HostInfo {
  hostname: string;
  ip_address?: string;
  os: string;
  os_version?: string;
  kernel?: string;
  architecture?: string;
  uptime?: string;
  cpu_count?: number;
  memory_total?: string;
  disk_total?: string;
  network_interfaces?: string[];
}

// Agent 上下文
export interface AgentContext {
  connected: boolean;
  host_info?: HostInfo | null;
  summary?: string | null;
  error?: string;
}

// Skill 结果
export interface SkillResult {
  skill_name: string;
  summary: string;
  risk_level: string;
  recommendations: string[];
  findings_count: number;
}

// Agent 步骤结果
export interface StepResult {
  tool_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  duration_ms: number;
  error?: string;
  output?: any;
}

// Agent 执行摘要
export interface ExecutionSummary {
  total_steps: number;
  successful_steps: number;
  failed_steps: number;
  total_duration_ms: number;
}

// 结构化输出
export interface StructuredOutput {
  execution_id: string;
  plan_id: string;
  request_id: string;
  status: string;
  summary: ExecutionSummary;
  skill_results: SkillResult[];
  steps: StepResult[];
}

// Agent 证据项（兼容字符串和对象）
export type AgentEvidenceItem =
  | string
  | {
      title?: string;
      detail?: string;
      source?: string;
      value?: any;
    };

// Agent 计划步骤（兼容新旧结构）
//
// 旧字段（兼容保留）: id, description, parameters
// 新字段（目标统一）: step_id, title, reason, tool_args
// 渲染时优先取新字段，旧字段兜底
export interface AgentPlanStep {
  id?: string;                  // 旧: 步骤 ID
  step_id?: string;             // 新: 步骤 ID
  step_number?: number;
  title?: string;               // 新: 步骤标题（优先使用）
  description?: string;         // 旧: 步骤描述（fallback）
  reason?: string;               // 新: 选择该步骤的原因
  skill_id?: string;
  skill_name?: string;
  tool_name?: string;
  parameters?: Record<string, any>; // 旧: 工具参数
  tool_args?: Record<string, any>;  // 新: 工具参数
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
}

// Agent 执行轨迹（兼容新旧结构）
//
// 旧字段（兼容保留）: tool_name, status, duration_ms, error
// 新字段（目标统一）: step_id, tool_result_summary, output_preview, success
// 渲染时 tool_result_summary 无则不显示，output_preview 超过 300 字符截断
export interface AgentExecutionTrace {
  id?: string;
  plan_id?: string;
  step_id: string;
  step_number?: number;
  title?: string;
  tool_name: string;
  tool_result_summary?: string;  // 新: 工具结果摘要
  output_preview?: string;       // 新: 输出预览（前端会截断到 300 字符）
  status: string;
  started_at?: string;
  completed_at?: string;
  duration_ms: number;
  success?: boolean;
  error?: string;
}

// Agent 最终响应
export interface AgentFinalResponse {
  summary: string;
  evidence: AgentEvidenceItem[];
  risks: string[];
  recommendations: string[];
  commands: string[];
  next_actions: string[];
}

// Agent 运行结果
export interface AgentRunResult {
  id: string;
  request_id: string;
  task: string;
  status: 'running' | 'completed' | 'failed';
  skill_name?: string;
  plan?: {
    id?: string;
    request_id?: string;
    steps: AgentPlanStep[];
    status?: string;
  } | AgentPlanStep[];
  traces: AgentExecutionTrace[];
  final?: AgentFinalResponse;
  skill_results: SkillResult[];
  structured_output?: AgentStructuredOutput;
  total_duration_ms: number;
  created_at: string;
  raw_summary?: string;
}

// Agent 结构化输出（兼容增强）
export interface AgentStructuredOutput {
  execution_id?: string;
  plan_id?: string;
  request_id?: string;
  status?: string;
  summary?: {
    total_steps?: number;
    successful_steps?: number;
    failed_steps?: number;
    total_duration_ms?: number;
  };
  skill_results?: {
    skill_name: string;
    risk_level: string;
    recommendations: string[];
    findings_count: number;
  }[];
  steps?: StepExecution[];
}

// 步骤执行记录（兼容增强）
export interface StepExecution {
  step_id?: string;
  step_number?: number;
  tool_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  duration_ms?: number;
  output?: any;
  error?: string;
}

// Agent 模式类型
export type AgentMode = 'normal' | 'agent';

// Skill 快捷入口
export interface SkillShortcut {
  id: string;
  name: string;
  description: string;
  icon: string;
  keywords: string[];
}

// Agent 执行状态
export interface AgentExecutionState {
  isRunning: boolean;
  currentStep: number;
  totalSteps: number;
  status: 'idle' | 'planning' | 'executing' | 'summarizing' | 'completed' | 'failed';
  result?: AgentRunResult;
  error?: string;
}

// Skill 选择项
export interface SkillSelection {
  skill: SkillDefinition;
  selected: boolean;
}
