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

// Agent 运行结果
export interface AgentRunResult {
  id: string;
  request_id: string;
  task: string;
  status: 'running' | 'completed' | 'failed';
  skill_results: SkillResult[];
  structured_output: AgentStructuredOutput;
  total_duration_ms: number;
  created_at: string;
  raw_summary?: string;
}

// Agent 结构化输出
export interface AgentStructuredOutput {
  execution_id: string;
  plan_id: string;
  request_id: string;
  status: string;
  summary: {
    total_steps: number;
    successful_steps: number;
    failed_steps: number;
    total_duration_ms: number;
  };
  skill_results: {
    skill_name: string;
    risk_level: string;
    recommendations: string[];
    findings_count: number;
  }[];
  steps: StepExecution[];
}

// 步骤执行记录
export interface StepExecution {
  step_id: string;
  step_number: number;
  tool_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  duration_ms: number;
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
