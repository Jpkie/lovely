/**
 * Agent 服务
 * 调用后端 Agent API
 */

import type {
  AgentRunRequest,
  AgentRunResult,
  AgentContext,
  SkillDefinition,
  ToolDefinition,
} from './agentTypes';
import { invoke as tauriInvoke } from '../../shims/@tauri-apps/api/core';

async function invoke(cmd: string, args?: Record<string, unknown>): Promise<any> {
  return tauriInvoke(cmd, args as any);
}

/**
 * Agent 服务类
 */
export class AgentService {
  private static instance: AgentService;

  private constructor() {}

  public static getInstance(): AgentService {
    if (!AgentService.instance) {
      AgentService.instance = new AgentService();
    }
    return AgentService.instance;
  }

  /**
   * 运行 Agent 任务
   */
  public async runAgentTask(request: AgentRunRequest): Promise<AgentRunResult> {
    try {
      const result = await invoke('agent_run', { req: request });
      return result;
    } catch (error) {
      console.error('Agent run failed:', error);
      throw error;
    }
  }

  /**
   * 获取 Agent 上下文
   */
  public async getAgentContext(): Promise<AgentContext> {
    try {
      const result = await invoke('agent_context');
      return result;
    } catch (error) {
      console.error('Failed to get agent context:', error);
      return { connected: false, host_info: null, summary: null };
    }
  }

  /**
   * 获取可用工具列表
   */
  public async getTools(): Promise<{ tools: ToolDefinition[]; count: number }> {
    try {
      const result = await invoke('agent_tools');
      return result;
    } catch (error) {
      console.error('Failed to get tools:', error);
      return { tools: [], count: 0 };
    }
  }

  /**
   * 获取可用 Skills 列表
   */
  public async getSkills(): Promise<{ skills: SkillDefinition[]; count: number }> {
    try {
      const result = await invoke('agent_skills');
      return result;
    } catch (error) {
      console.error('Failed to get skills:', error);
      return { skills: [], count: 0 };
    }
  }

  /**
   * 获取 Agent 配置
   */
  public async getAgentSettings(): Promise<any> {
    try {
      const settings = await invoke('read_settings_file');
      let parsed: any = {};

      if (typeof settings === 'string') {
        parsed = JSON.parse(settings || '{}');
      } else if (settings && typeof settings === 'object') {
        if (settings.content) {
          parsed = JSON.parse(settings.content || '{}');
        } else {
          parsed = settings;
        }
      }

      return parsed.agent || null;
    } catch (error) {
      console.error('Failed to get agent settings:', error);
      return null;
    }
  }

  /**
   * 统一读取 settings JSON
   */
  public async readSettingsJson(): Promise<any> {
    try {
      const result = await invoke('read_settings_file');
      if (typeof result === 'string') {
        return JSON.parse(result);
      }
      if (result && result.content) {
        return JSON.parse(result.content);
      }
      return result || {};
    } catch (error) {
      console.error('Failed to read settings:', error);
      return {};
    }
  }
}

// 导出单例实例
export const agentService = AgentService.getInstance();
