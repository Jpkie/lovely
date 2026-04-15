/**
 * Agent 上下文构建器
 * 用于构建和格式化 Agent 任务上下文
 */

import type { HostInfo } from './agentTypes';

/**
 * 格式化主机信息为可读字符串
 */
export function formatHostInfo(hostInfo: HostInfo): string {
  const lines: string[] = [];

  lines.push(`主机名: ${hostInfo.hostname}`);
  if (hostInfo.ip_address) {
    lines.push(`IP 地址: ${hostInfo.ip_address}`);
  }
  lines.push(`操作系统: ${hostInfo.os}`);
  if (hostInfo.os_version) {
    lines.push(`版本: ${hostInfo.os_version}`);
  }
  if (hostInfo.kernel) {
    lines.push(`内核: ${hostInfo.kernel}`);
  }
  if (hostInfo.architecture) {
    lines.push(`架构: ${hostInfo.architecture}`);
  }
  if (hostInfo.uptime) {
    lines.push(`运行时间: ${hostInfo.uptime}`);
  }
  if (hostInfo.cpu_count) {
    lines.push(`CPU 核心数: ${hostInfo.cpu_count}`);
  }
  if (hostInfo.memory_total) {
    lines.push(`总内存: ${hostInfo.memory_total}`);
  }
  if (hostInfo.disk_total) {
    lines.push(`总磁盘: ${hostInfo.disk_total}`);
  }

  return lines.join('\n');
}

/**
 * 格式化 Skill 结果为字符串
 */
export function formatSkillResults(skillResults: any[]): string {
  if (!skillResults || skillResults.length === 0) {
    return '无 Skill 执行结果';
  }

  const lines: string[] = ['## Skill 执行结果\n'];

  for (const result of skillResults) {
    lines.push(`### ${result.skill_name}`);
    lines.push(`- 风险等级: ${result.risk_level}`);
    if (result.recommendations && result.recommendations.length > 0) {
      lines.push('- 建议:');
      for (const rec of result.recommendations) {
        lines.push(`  - ${rec}`);
      }
    }
    lines.push('');
  }

  return lines.join('\n');
}

/**
 * 格式化执行步骤为可读字符串
 */
export function formatExecutionSteps(steps: any[]): string {
  if (!steps || steps.length === 0) {
    return '无执行步骤';
  }

  const lines: string[] = ['## 执行步骤\n'];

  for (const step of steps) {
    const icon = step.status === 'completed' ? '✓' : step.status === 'failed' ? '✗' : '○';
    lines.push(`${icon} [${step.step_number || step.tool_name}] ${step.tool_name}`);
    if (step.duration_ms) {
      lines.push(`   耗时: ${step.duration_ms}ms`);
    }
    if (step.error) {
      lines.push(`   错误: ${step.error}`);
    }
  }

  return lines.join('\n');
}

/**
 * 渲染 Agent 结果面板 HTML
 */
export function renderAgentResultPanel(result: any): string {
  const statusColor = result.status === 'completed' ? 'var(--success-color)' : 'var(--error-color)';
  const statusText = result.status === 'completed' ? '已完成' : result.status === 'failed' ? '失败' : '运行中';

  return `
    <div class="agent-result-panel" style="
      display: flex;
      flex-direction: column;
      gap: 16px;
      height: 100%;
      overflow: auto;
    ">
      <div class="agent-result-header" style="
        padding: 16px;
        background: var(--bg-secondary);
        border-radius: 12px;
        border: 1px solid var(--border-color);
      ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <h3 style="margin: 0; color: var(--text-primary);">Agent 执行结果</h3>
          <span style="
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            background: ${statusColor}22;
            color: ${statusColor};
          ">${statusText}</span>
        </div>
        <div style="font-size: 13px; color: var(--text-secondary);">
          任务: ${result.task || 'N/A'}
        </div>
        <div style="font-size: 12px; color: var(--text-secondary); margin-top: 8px;">
          总耗时: ${result.total_duration_ms || 0}ms
        </div>
      </div>

      ${result.skill_results && result.skill_results.length > 0 ? `
        <div class="agent-skill-results" style="
          padding: 16px;
          background: var(--bg-secondary);
          border-radius: 12px;
          border: 1px solid var(--border-color);
        ">
          <h4 style="margin: 0 0 12px; color: var(--text-primary);">Skill 结果</h4>
          ${result.skill_results.map((sr: any) => `
            <div style="margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid var(--border-color);">
              <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <strong style="color: var(--text-primary);">${sr.skill_name}</strong>
                <span style="
                  padding: 2px 8px;
                  border-radius: 12px;
                  font-size: 11px;
                  background: ${sr.risk_level === 'high' ? 'var(--error-color)' : sr.risk_level === 'medium' ? 'var(--warning-color)' : 'var(--success-color)'}22;
                  color: ${sr.risk_level === 'high' ? 'var(--error-color)' : sr.risk_level === 'medium' ? 'var(--warning-color)' : 'var(--success-color)'};
                ">${sr.risk_level || 'unknown'}</span>
              </div>
              ${sr.recommendations && sr.recommendations.length > 0 ? `
                <div style="font-size: 12px; color: var(--text-secondary);">
                  ${sr.recommendations.map((r: string) => `<div style="margin-bottom: 4px;">• ${r}</div>`).join('')}
                </div>
              ` : ''}
            </div>
          `).join('')}
        </div>
      ` : ''}

      ${result.structured_output && result.structured_output.steps ? `
        <div class="agent-steps" style="
          padding: 16px;
          background: var(--bg-secondary);
          border-radius: 12px;
          border: 1px solid var(--border-color);
        ">
          <h4 style="margin: 0 0 12px; color: var(--text-primary);">执行步骤</h4>
          <div style="display: flex; flex-direction: column; gap: 8px;">
            ${result.structured_output.steps.map((step: any) => {
              const icon = step.status === 'completed' ? '✓' : step.status === 'failed' ? '✗' : '○';
              const color = step.status === 'completed' ? 'var(--success-color)' : step.status === 'failed' ? 'var(--error-color)' : 'var(--text-secondary)';
              return `
                <div style="
                  display: flex;
                  align-items: center;
                  gap: 8px;
                  padding: 8px 12px;
                  background: var(--bg-tertiary);
                  border-radius: 8px;
                  font-size: 13px;
                ">
                  <span style="color: ${color}; font-weight: bold;">${icon}</span>
                  <span style="color: var(--text-primary);">${step.tool_name}</span>
                  <span style="margin-left: auto; color: var(--text-secondary); font-size: 12px;">${step.duration_ms || 0}ms</span>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      ` : ''}
    </div>
  `;
}

/**
 * 构建快速任务提示
 */
export function buildQuickTaskHints(): string[] {
  return [
    '检查主机端口和安全配置',
    '分析系统日志发现异常',
    '查找可疑进程',
    '审计 SSH 配置',
    '进行全面安全检测',
  ];
}

/**
 * 判断是否为 Agent 模式任务
 */
export function isAgentModeTask(task: string): boolean {
  const agentKeywords = [
    '检测', '扫描', '分析', '审计', '调查', '评估',
    '检查', '排查', '发现', '监控', '健康检查',
    '安全', '端口', '进程', '日志', 'SSH',
  ];

  const lowerTask = task.toLowerCase();
  return agentKeywords.some(keyword => lowerTask.includes(keyword));
}
