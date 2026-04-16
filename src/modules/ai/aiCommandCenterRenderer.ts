/**
 * AI 命令中心渲染器
 * AI 模式首页工作台 - 真正的 AI 指挥中心
 */

import { agentService } from './agentService';
import { BUILTIN_SKILL_SHORTCUTS } from './skillRegistry';
import type { AgentRunRequest, AgentRunResult } from './agentTypes';
import {
  Send,
  Message,
  CheckOne,
  CloseOne,
  Refresh,
  Copy,
  Loading,
  LinkCloud,
  Connection,
  Plus,
  Terminal,
  Rocket,
  Shield,
  Log,
  FileText,
  User
} from '@icon-park/svg';

export interface TaskHistoryItem {
  id: string;
  task: string;
  skills: string[];
  status: 'completed' | 'failed' | 'running';
  timestamp: number;
  result?: AgentRunResult;
}

export class AICommandCenterRenderer {
  private taskHistory: TaskHistoryItem[] = [];
  private currentTask: string = '';
  private selectedSkills: string[] = [];
  private isRunning: boolean = false;
  private currentResult?: AgentRunResult;

  constructor() {
    this.loadHistory();
  }

  /**
   * 获取连接状态
   */
  private getConnectionState(): { isConnected: boolean; serverInfo?: any } {
    const stateManager = (window as any).app?.stateManager;
    const state = stateManager?.getState();
    return {
      isConnected: state?.isConnected || false,
      serverInfo: state?.serverInfo
    };
  }

  /**
   * 渲染 AI 命令中心主界面
   */
  render(): string {
    const { isConnected, serverInfo } = this.getConnectionState();

    return `
      <div class="ai-command-center">
        <!-- 顶部区域：标题 + 输入区 -->
        ${this.renderHeader(isConnected)}

        <!-- 中部：技能卡片 + 主机状态 -->
        <div class="ai-command-center-main">
          <!-- 左侧：技能卡片快捷入口 -->
          <div class="ai-skill-panel">
            ${this.renderSkillCards()}
          </div>

          <!-- 右侧：主机状态面板 -->
          <div class="ai-host-panel">
            ${this.renderHostStatus(isConnected, serverInfo)}
          </div>
        </div>

        <!-- 底部：执行结果区域 -->
        <div class="ai-result-panel">
          ${this.renderResultArea()}
        </div>
      </div>

      <style>
        .ai-command-center {
          display: flex;
          flex-direction: column;
          height: 100%;
          padding: var(--spacing-md);
          gap: var(--spacing-md);
          overflow: hidden;
        }

        .ai-command-center-main {
          display: grid;
          grid-template-columns: 1fr 340px;
          gap: var(--spacing-md);
          flex: 1;
          min-height: 0;
        }

        .ai-skill-panel {
          background: var(--bg-secondary);
          border: 1px solid var(--border-color);
          border-radius: var(--border-radius-lg);
          padding: var(--spacing-md);
          overflow-y: auto;
        }

        .ai-host-panel {
          background: var(--bg-secondary);
          border: 1px solid var(--border-color);
          border-radius: var(--border-radius-lg);
          padding: var(--spacing-md);
          overflow-y: auto;
        }

        .ai-result-panel {
          background: var(--bg-secondary);
          border: 1px solid var(--border-color);
          border-radius: var(--border-radius-lg);
          padding: var(--spacing-md);
          min-height: 180px;
          max-height: 280px;
          overflow-y: auto;
        }

        /* 顶部标题区域 */
        .ai-header {
          background: linear-gradient(135deg, var(--primary-color) 0%, #8b5cf6 100%);
          border-radius: var(--border-radius-lg);
          padding: var(--spacing-lg);
          color: white;
        }

        .ai-header-title {
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
          margin-bottom: var(--spacing-xs);
        }

        .ai-header-title h1 {
          font-size: 20px;
          font-weight: 600;
          margin: 0;
        }

        .ai-header-subtitle {
          font-size: 13px;
          opacity: 0.9;
          margin-bottom: var(--spacing-md);
        }

        /* 命令输入框样式 */
        .ai-command-input-wrapper {
          display: flex;
          gap: var(--spacing-sm);
          background: rgba(255, 255, 255, 0.15);
          backdrop-filter: blur(10px);
          border: 1px solid rgba(255, 255, 255, 0.2);
          border-radius: var(--border-radius);
          padding: var(--spacing-xs);
        }

        .ai-command-input {
          flex: 1;
          background: transparent;
          border: none;
          outline: none;
          font-size: 14px;
          color: white;
          padding: var(--spacing-sm);
          resize: none;
          min-height: 44px;
          max-height: 100px;
          font-family: inherit;
        }

        .ai-command-input::placeholder {
          color: rgba(255, 255, 255, 0.6);
        }

        .ai-command-submit {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 44px;
          height: 44px;
          background: white;
          border: none;
          border-radius: var(--border-radius);
          color: var(--primary-color);
          cursor: pointer;
          transition: all 0.2s;
          flex-shrink: 0;
        }

        .ai-command-submit:hover:not(:disabled) {
          transform: scale(1.05);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }

        .ai-command-submit:disabled {
          opacity: 0.5;
          cursor: not-allowed;
          transform: none;
        }

        /* 技能卡片样式 */
        .ai-skill-section {
          margin-bottom: var(--spacing-md);
        }

        .ai-section-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: var(--spacing-sm);
        }

        .ai-section-title {
          font-size: 13px;
          font-weight: 600;
          color: var(--text-primary);
        }

        .ai-section-hint {
          font-size: 11px;
          color: var(--text-tertiary);
        }

        .ai-skill-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
          gap: var(--spacing-sm);
        }

        .ai-skill-card {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 6px;
          padding: var(--spacing-md);
          background: var(--bg-primary);
          border: 1px solid var(--border-color);
          border-radius: var(--border-radius);
          cursor: pointer;
          transition: all 0.2s;
          text-align: center;
        }

        .ai-skill-card:hover {
          border-color: var(--primary-color);
          background: var(--bg-tertiary);
          transform: translateY(-2px);
        }

        .ai-skill-card.selected {
          border-color: var(--primary-color);
          background: rgba(59, 130, 246, 0.1);
          box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
        }

        .ai-skill-icon {
          font-size: 28px;
          line-height: 1;
        }

        .ai-skill-name {
          font-size: 12px;
          font-weight: 500;
          color: var(--text-primary);
        }

        .ai-skill-desc {
          font-size: 10px;
          color: var(--text-secondary);
          line-height: 1.3;
        }

        /* 技能标签 */
        .ai-selected-skills {
          margin-top: var(--spacing-md);
          padding-top: var(--spacing-sm);
          border-top: 1px solid var(--border-color);
        }

        .ai-selected-label {
          font-size: 11px;
          color: var(--text-tertiary);
          margin-bottom: var(--spacing-xs);
          display: block;
        }

        .ai-skill-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
        }

        .ai-skill-tag {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 4px 8px;
          background: rgba(59, 130, 246, 0.1);
          border: 1px solid var(--primary-color);
          border-radius: 4px;
          font-size: 11px;
          color: var(--primary-color);
        }

        .ai-skill-tag-remove {
          cursor: pointer;
          opacity: 0.7;
        }

        .ai-skill-tag-remove:hover {
          opacity: 1;
        }

        /* 主机状态样式 */
        .ai-host-header {
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
          margin-bottom: var(--spacing-md);
          padding-bottom: var(--spacing-sm);
          border-bottom: 1px solid var(--border-color);
        }

        .ai-host-title {
          font-size: 14px;
          font-weight: 600;
          color: var(--text-primary);
        }

        .ai-host-info {
          display: flex;
          flex-direction: column;
          gap: var(--spacing-sm);
        }

        .ai-host-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 12px;
          padding: 6px 0;
        }

        .ai-host-label {
          color: var(--text-secondary);
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .ai-host-value {
          color: var(--text-primary);
          font-weight: 500;
        }

        .ai-host-value.connected {
          color: var(--success-color);
        }

        .ai-host-value.disconnected {
          color: var(--text-tertiary);
        }

        /* 未连接引导 */
        .ai-disconnected-guide {
          text-align: center;
          padding: var(--spacing-lg);
        }

        .ai-disconnected-icon {
          width: 64px;
          height: 64px;
          border-radius: 50%;
          background: var(--bg-tertiary);
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto var(--spacing-md);
          color: var(--text-tertiary);
        }

        .ai-disconnected-title {
          font-size: 14px;
          font-weight: 600;
          color: var(--text-primary);
          margin-bottom: var(--spacing-xs);
        }

        .ai-disconnected-desc {
          font-size: 12px;
          color: var(--text-secondary);
          margin-bottom: var(--spacing-md);
          line-height: 1.5;
        }

        .ai-connect-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 8px 16px;
          background: var(--primary-color);
          color: white;
          border: none;
          border-radius: var(--border-radius);
          font-size: 13px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .ai-connect-btn:hover {
          opacity: 0.9;
          transform: translateY(-1px);
        }

        /* 快速操作 */
        .ai-quick-actions {
          margin-top: var(--spacing-md);
          padding-top: var(--spacing-sm);
          border-top: 1px solid var(--border-color);
        }

        .ai-quick-actions-label {
          font-size: 11px;
          color: var(--text-tertiary);
          margin-bottom: var(--spacing-xs);
          display: block;
        }

        .ai-quick-buttons {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
        }

        .ai-quick-btn {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 6px 10px;
          background: var(--bg-primary);
          border: 1px solid var(--border-color);
          border-radius: 4px;
          font-size: 11px;
          color: var(--text-primary);
          cursor: pointer;
          transition: all 0.2s;
        }

        .ai-quick-btn:hover {
          border-color: var(--primary-color);
          background: var(--bg-tertiary);
        }

        /* 结果区域样式 */
        .ai-result-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: var(--spacing-md);
          padding-bottom: var(--spacing-sm);
          border-bottom: 1px solid var(--border-color);
        }

        .ai-result-title {
          font-size: 14px;
          font-weight: 600;
          color: var(--text-primary);
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
        }

        .ai-result-actions {
          display: flex;
          gap: var(--spacing-xs);
        }

        .ai-result-action-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 28px;
          height: 28px;
          background: var(--bg-tertiary);
          border: 1px solid var(--border-color);
          border-radius: var(--border-radius);
          color: var(--text-secondary);
          cursor: pointer;
          transition: all 0.2s;
        }

        .ai-result-action-btn:hover {
          background: var(--bg-primary);
          color: var(--text-primary);
        }

        .ai-result-content {
          font-size: 13px;
          color: var(--text-primary);
          line-height: 1.6;
          white-space: pre-wrap;
        }

        .ai-result-empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          color: var(--text-tertiary);
          gap: var(--spacing-sm);
        }

        .ai-result-empty-icon {
          font-size: 32px;
          opacity: 0.5;
        }

        /* 步骤列表样式 */
        .ai-steps-list {
          display: flex;
          flex-direction: column;
          gap: var(--spacing-xs);
          margin-top: var(--spacing-md);
        }

        .ai-step-item {
          display: flex;
          align-items: flex-start;
          gap: var(--spacing-sm);
          padding: var(--spacing-sm);
          background: var(--bg-primary);
          border-radius: var(--border-radius);
          font-size: 12px;
        }

        .ai-step-icon {
          flex-shrink: 0;
          margin-top: 2px;
        }

        .ai-step-content {
          flex: 1;
          min-width: 0;
        }

        .ai-step-title {
          font-weight: 500;
          color: var(--text-primary);
          margin-bottom: 2px;
        }

        .ai-step-desc {
          color: var(--text-secondary);
          font-size: 11px;
        }

        .ai-step-status {
          flex-shrink: 0;
          font-size: 10px;
          padding: 2px 6px;
          border-radius: 4px;
        }

        .ai-step-status.completed {
          background: rgba(34, 197, 94, 0.2);
          color: var(--success-color);
        }

        .ai-step-status.failed {
          background: rgba(239, 68, 68, 0.2);
          color: var(--error-color);
        }

        .ai-step-status.running {
          background: rgba(59, 130, 246, 0.2);
          color: var(--primary-color);
        }

        /* 历史记录样式 */
        .ai-history-section {
          margin-top: var(--spacing-md);
          padding-top: var(--spacing-sm);
          border-top: 1px solid var(--border-color);
        }

        .ai-history-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: var(--spacing-sm);
        }

        .ai-history-title {
          font-size: 13px;
          font-weight: 600;
          color: var(--text-primary);
        }

        .ai-history-clear {
          background: none;
          border: none;
          color: var(--text-tertiary);
          font-size: 11px;
          cursor: pointer;
          padding: 2px 6px;
        }

        .ai-history-list {
          display: flex;
          flex-direction: column;
          gap: var(--spacing-xs);
          max-height: 120px;
          overflow-y: auto;
        }

        .ai-history-item {
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
          padding: var(--spacing-sm);
          background: var(--bg-primary);
          border-radius: var(--border-radius);
          cursor: pointer;
          transition: all 0.2s;
          font-size: 12px;
        }

        .ai-history-item:hover {
          background: var(--bg-tertiary);
        }

        .ai-history-task {
          flex: 1;
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          color: var(--text-primary);
        }

        .ai-history-time {
          color: var(--text-tertiary);
          font-size: 11px;
          flex-shrink: 0;
        }

        /* 加载状态 */
        .ai-loading {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: var(--spacing-sm);
          padding: var(--spacing-lg);
          color: var(--text-secondary);
        }

        .ai-loading-spinner {
          width: 20px;
          height: 20px;
          border: 2px solid var(--border-color);
          border-top-color: var(--primary-color);
          border-radius: 50%;
          animation: ai-spin 1s linear infinite;
        }

        @keyframes ai-spin {
          to { transform: rotate(360deg); }
        }
      </style>
    `;
  }

  /**
   * 渲染顶部标题区
   */
  private renderHeader(isConnected: boolean): string {
    return `
      <div class="ai-header">
        <div class="ai-header-title">
          <span style="font-size: 24px;">🎯</span>
          <h1>AI 指挥台</h1>
          <button
            class="ai-switch-mode-btn"
            onclick="window.app.stateManager.setCurrentPage('dashboard'); window.app.render()"
            title="切换到工具箱模式"
            style="
              margin-left: auto;
              padding: 6px 14px;
              background: rgba(255,255,255,0.2);
              border: 1px solid rgba(255,255,255,0.3);
              border-radius: 6px;
              color: white;
              font-size: 12px;
              font-weight: 500;
              cursor: pointer;
              backdrop-filter: blur(6px);
              transition: all 0.2s;
              white-space: nowrap;
            "
            onmouseover="this.style.background='rgba(255,255,255,0.3)'"
            onmouseout="this.style.background='rgba(255,255,255,0.2)'"
          >🔧 工具箱版</button>
        </div>
        <div class="ai-header-subtitle">
          一句话下达任务，AI 帮你分析主机并执行检测
        </div>
        <div class="ai-command-input-wrapper">
          <textarea
            id="ai-command-input"
            class="ai-command-input"
            placeholder="${isConnected ? '输入任务描述，如：帮我检查系统安全、查看异常登录日志...' : '连接服务器后即可下达 AI 任务...'}"
            rows="1"
            ${this.isRunning || !isConnected ? 'disabled' : ''}
          ></textarea>
          <button
            id="ai-command-submit"
            class="ai-command-submit"
            ${this.isRunning || !isConnected ? 'disabled' : ''}
            onclick="window.aiCommandCenter?.executeTask()"
          >
            ${this.isRunning
              ? `<div class="ai-loading-spinner" style="width: 18px; height: 18px; border-width: 2px; border-color: var(--primary-color); border-top-color: transparent;"></div>`
              : Send({ theme: 'outline', size: '18', fill: 'currentColor' })
            }
          </button>
        </div>
      </div>
    `;
  }

  /**
   * 渲染技能卡片
   */
  private renderSkillCards(): string {
    const shortcuts = BUILTIN_SKILL_SHORTCUTS;

    return `
      <div class="ai-skill-section">
        <div class="ai-section-header">
          <span class="ai-section-title">🎯 技能快捷入口</span>
          <span class="ai-section-hint">点击选择技能</span>
        </div>
        <div class="ai-skill-grid">
          ${shortcuts.map(shortcut => {
            const isSelected = this.selectedSkills.includes(shortcut.id);
            return `
              <div
                class="ai-skill-card ${isSelected ? 'selected' : ''}"
                onclick="window.aiCommandCenter?.toggleSkill('${shortcut.id}')"
                data-skill-id="${shortcut.id}"
              >
                <span class="ai-skill-icon">${shortcut.icon}</span>
                <span class="ai-skill-name">${shortcut.name}</span>
                <span class="ai-skill-desc">${shortcut.description}</span>
              </div>
            `;
          }).join('')}
        </div>
      </div>

      <!-- 已选技能标签 -->
      ${this.selectedSkills.length > 0 ? `
        <div class="ai-selected-skills">
          <span class="ai-selected-label">已选技能：</span>
          <div class="ai-skill-tags">
            ${this.selectedSkills.map(skillId => {
              const skill = shortcuts.find(s => s.id === skillId);
              return skill ? `
                <span class="ai-skill-tag">
                  ${skill.icon} ${skill.name}
                  <span class="ai-skill-tag-remove" onclick="event.stopPropagation(); window.aiCommandCenter?.toggleSkill('${skillId}')">×</span>
                </span>
              ` : '';
            }).join('')}
          </div>
        </div>
      ` : ''}

      <!-- 最近任务历史 -->
      <div class="ai-history-section">
        <div class="ai-history-header">
          <span class="ai-history-title">📋 最近任务</span>
          ${this.taskHistory.length > 0 ? `
            <button class="ai-history-clear" onclick="window.aiCommandCenter?.clearHistory()">清空</button>
          ` : ''}
        </div>
        <div class="ai-history-list">
          ${this.taskHistory.length > 0 ? this.taskHistory.slice(0, 5).map(item => `
            <div class="ai-history-item" onclick="window.aiCommandCenter?.loadHistoryItem('${item.id}')">
              <span class="ai-step-icon">
                ${item.status === 'completed'
                  ? CheckOne({ theme: 'filled', size: '14', fill: 'var(--success-color)' })
                  : item.status === 'failed'
                    ? CloseOne({ theme: 'filled', size: '14', fill: 'var(--error-color)' })
                    : Loading({ theme: 'outline', size: '14', fill: 'var(--primary-color)' })
                }
              </span>
              <span class="ai-history-task">${this.escapeHtml(item.task.substring(0, 40))}${item.task.length > 40 ? '...' : ''}</span>
              <span class="ai-history-time">${this.formatTime(item.timestamp)}</span>
            </div>
          `).join('') : `
            <div style="text-align: center; padding: var(--spacing-md); color: var(--text-tertiary); font-size: 12px;">
              暂无任务历史
            </div>
          `}
        </div>
      </div>
    `;
  }

  /**
   * 渲染主机状态面板
   */
  private renderHostStatus(isConnected: boolean, serverInfo?: any): string {
    return `
      <div class="ai-host-header">
        <span style="font-size: 16px;">${Message({ theme: 'outline', size: '16', fill: 'currentColor' })}</span>
        <span class="ai-host-title">主机状态</span>
      </div>

      <div class="ai-host-info">
        <div class="ai-host-item">
          <span class="ai-host-label">${Connection({ theme: 'outline', size: '14', fill: 'currentColor' })} 连接状态</span>
          <span class="ai-host-value ${isConnected ? 'connected' : 'disconnected'}">
            ${isConnected ? '● 已连接' : '○ 未连接'}
          </span>
        </div>

        ${isConnected && serverInfo ? `
          <div class="ai-host-item">
            <span class="ai-host-label">${FileText({ theme: 'outline', size: '14', fill: 'currentColor' })} 主机名</span>
            <span class="ai-host-value">${serverInfo.name || serverInfo.host || 'N/A'}</span>
          </div>
          <div class="ai-host-item">
            <span class="ai-host-label">${Log({ theme: 'outline', size: '14', fill: 'currentColor' })} IP地址</span>
            <span class="ai-host-value">${serverInfo.host || 'N/A'}</span>
          </div>
          <div class="ai-host-item">
            <span class="ai-host-label">${User({ theme: 'outline', size: '14', fill: 'currentColor' })} 用户名</span>
            <span class="ai-host-value">${serverInfo.username || 'N/A'}</span>
          </div>
        ` : ''}

        ${!isConnected ? `
          <div class="ai-disconnected-guide">
            <div class="ai-disconnected-icon">
              ${LinkCloud({ theme: 'outline', size: '32', fill: 'currentColor' })}
            </div>
            <div class="ai-disconnected-title">未连接服务器</div>
            <div class="ai-disconnected-desc">
              当前未连接服务器，请先建立 SSH 连接后执行主机任务
            </div>
            <button class="ai-connect-btn" onclick="window.aiCommandCenter?.openConnection()">
              ${Plus({ theme: 'outline', size: '14', fill: 'currentColor' })}
              连接服务器
            </button>
          </div>
        ` : ''}

        <!-- 快速操作 -->
        ${isConnected ? `
          <div class="ai-quick-actions">
            <span class="ai-quick-actions-label">快速操作</span>
            <div class="ai-quick-buttons">
              <button class="ai-quick-btn" onclick="window.aiCommandCenter?.quickTask('检查系统安全状态')">
                ${Shield({ theme: 'outline', size: '12', fill: 'currentColor' })} 安全检查
              </button>
              <button class="ai-quick-btn" onclick="window.aiCommandCenter?.quickTask('查看异常登录日志')">
                ${Log({ theme: 'outline', size: '12', fill: 'currentColor' })} 登录日志
              </button>
              <button class="ai-quick-btn" onclick="window.aiCommandCenter?.quickTask('检查可疑进程')">
                ${Terminal({ theme: 'outline', size: '12', fill: 'currentColor' })} 可疑进程
              </button>
              <button class="ai-quick-btn" onclick="window.aiCommandCenter?.quickTask('检查系统资源使用情况')">
                ${Rocket({ theme: 'outline', size: '12', fill: 'currentColor' })} 资源情况
              </button>
            </div>
          </div>
        ` : ''}
      </div>
    `;
  }

  /**
   * 渲染结果区域
   */
  private renderResultArea(): string {
    if (this.isRunning) {
      return `
        <div class="ai-result-header">
          <span class="ai-result-title">
            ${Refresh({ theme: 'outline', size: '16', fill: 'currentColor' })}
            <span>执行中...</span>
          </span>
        </div>
        <div class="ai-loading">
          <div class="ai-loading-spinner"></div>
          <span>AI 正在处理任务</span>
        </div>
      `;
    }

    if (!this.currentResult) {
      return `
        <div class="ai-result-header">
          <span class="ai-result-title">
            ${Message({ theme: 'outline', size: '16', fill: 'currentColor' })}
            <span>执行结果</span>
          </span>
        </div>
        <div class="ai-result-empty">
          <span class="ai-result-empty-icon">💬</span>
          <span>输入任务描述开始 AI 对话</span>
        </div>
      `;
    }

    return `
      <div class="ai-result-header">
        <span class="ai-result-title">
          ${this.currentResult.status === 'completed'
            ? CheckOne({ theme: 'filled', size: '16', fill: 'var(--success-color)' })
            : CloseOne({ theme: 'filled', size: '16', fill: 'var(--error-color)' })
          }
          <span>${this.currentResult.status === 'completed' ? '执行完成' : '执行失败'}</span>
        </span>
        <div class="ai-result-actions">
          <button class="ai-result-action-btn" onclick="window.aiCommandCenter?.copyResult()" title="复制结果">
            ${Copy({ theme: 'outline', size: '14', fill: 'currentColor' })}
          </button>
          <button class="ai-result-action-btn" onclick="window.aiCommandCenter?.refreshResult()" title="刷新">
            ${Refresh({ theme: 'outline', size: '14', fill: 'currentColor' })}
          </button>
        </div>
      </div>

      <div class="ai-result-content">
        ${this.renderResultContent()}
      </div>

      ${this.renderStepsList()}
    `;
  }

  /**
   * 渲染结果内容
   */
  private renderResultContent(): string {
    if (!this.currentResult) return '';

    const final = this.currentResult.final;
    if (final) {
      let content = `<div style="margin-bottom: var(--spacing-md);">`;
      content += `<strong>📝 执行摘要：</strong>\n${final.summary}</div>`;

      if (final.recommendations && final.recommendations.length > 0) {
        content += `<div style="margin-bottom: var(--spacing-sm);"><strong>💡 建议：</strong></div>`;
        content += `<ul style="margin: 0; padding-left: 20px;">`;
        final.recommendations.forEach((rec: string) => {
          content += `<li style="margin-bottom: 4px;">${this.escapeHtml(rec)}</li>`;
        });
        content += `</ul>`;
      }

      if (final.commands && final.commands.length > 0) {
        content += `<div style="margin-top: var(--spacing-md);"><strong>🔧 执行的命令：</strong></div>`;
        content += `<div style="background: var(--bg-tertiary); padding: var(--spacing-sm); border-radius: 4px; margin-top: 4px;">`;
        final.commands.forEach((cmd: string) => {
          content += `<div style="font-family: var(--font-mono); font-size: 12px; margin-bottom: 4px;">`;
          content += `<span style="color: var(--text-tertiary);">$ </span>${this.escapeHtml(cmd)}`;
          content += `</div>`;
        });
        content += `</div>`;
      }

      content += `</div>`;
      return content;
    }

    if (this.currentResult.raw_summary) {
      return this.currentResult.raw_summary;
    }

    return '任务执行完成，无详细结果';
  }

  /**
   * 渲染步骤列表
   */
  private renderStepsList(): string {
    const traces = this.currentResult?.traces || [];
    const plan = this.currentResult?.plan;

    if (traces.length === 0 && (!plan || (Array.isArray(plan) && plan.length === 0))) {
      return '';
    }

    let steps: any[] = [];

    if (Array.isArray(plan) && plan.length > 0) {
      steps = plan;
    }

    if (traces.length > 0) {
      steps = traces;
    }

    if (steps.length === 0) return '';

    return `
      <div class="ai-steps-list">
        <div style="font-size: 12px; font-weight: 600; color: var(--text-secondary); margin-bottom: var(--spacing-xs);">
          执行步骤：
        </div>
        ${steps.slice(0, 10).map((step: any, idx: number) => {
          const title = step.title || step.description || step.tool_name || `步骤 ${idx + 1}`;
          const status = step.status || 'completed';
          return `
            <div class="ai-step-item">
              <span class="ai-step-icon">
                ${status === 'completed'
                  ? CheckOne({ theme: 'filled', size: '14', fill: 'var(--success-color)' })
                  : status === 'failed'
                    ? CloseOne({ theme: 'filled', size: '14', fill: 'var(--error-color)' })
                    : Refresh({ theme: 'outline', size: '14', fill: 'var(--primary-color)' })
                }
              </span>
              <div class="ai-step-content">
                <div class="ai-step-title">${this.escapeHtml(title)}</div>
                ${step.tool_name ? `<div class="ai-step-desc">工具: ${step.tool_name}</div>` : ''}
                ${step.error ? `<div class="ai-step-desc" style="color: var(--error-color);">错误: ${this.escapeHtml(step.error)}</div>` : ''}
              </div>
              <span class="ai-step-status ${status}">${this.getStatusLabel(status)}</span>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  /**
   * 打开连接面板
   */
  openConnection(): void {
    const modernUIRenderer = (window as any).app?.modernUIRenderer;

    if (modernUIRenderer?.showServerModal) {
      modernUIRenderer.showServerModal();
    }
  }

  /**
   * 切换技能选择
   */
  toggleSkill(skillId: string): void {
    const idx = this.selectedSkills.indexOf(skillId);
    if (idx >= 0) {
      this.selectedSkills.splice(idx, 1);
    } else {
      this.selectedSkills.push(skillId);
    }
    this.updateSkillCards();
  }

  /**
   * 更新技能卡片选中状态
   */
  private updateSkillCards(): void {
    const cards = document.querySelectorAll('.ai-skill-card');
    cards.forEach(card => {
      const skillId = (card as HTMLElement).dataset.skillId;
      if (skillId && this.selectedSkills.includes(skillId)) {
        card.classList.add('selected');
      } else {
        card.classList.remove('selected');
      }
    });
  }

  /**
   * 执行任务
   */
  async executeTask(): Promise<void> {
    const input = document.getElementById('ai-command-input') as HTMLTextAreaElement;
    if (!input) return;

    const task = input.value.trim();
    if (!task) return;

    const stateManager = (window as any).app?.stateManager;
    const state = stateManager?.getState();
    if (!state?.isConnected) {
      return;
    }

    this.currentTask = task;
    this.isRunning = true;
    this.currentResult = undefined;
    this.updateResultArea();

    const taskId = this.generateId();
    const historyItem: TaskHistoryItem = {
      id: taskId,
      task: task,
      skills: [...this.selectedSkills],
      status: 'running',
      timestamp: Date.now()
    };

    this.addToHistory(historyItem);

    try {
      const request: AgentRunRequest = {
        task: task,
        skills: this.selectedSkills.length > 0 ? this.selectedSkills : undefined,
        max_steps: 30
      };

      const result = await agentService.runAgentTask(request);

      this.currentResult = result;
      historyItem.status = result.status === 'completed' ? 'completed' : 'failed';
      historyItem.result = result;
      this.updateHistoryItem(historyItem);
    } catch (error: any) {
      console.error('任务执行失败:', error);
      historyItem.status = 'failed';
      this.updateHistoryItem(historyItem);

      this.currentResult = {
        id: taskId,
        request_id: taskId,
        task: task,
        status: 'failed',
        traces: [],
        skill_results: [],
        total_duration_ms: 0,
        created_at: new Date().toISOString(),
        raw_summary: `执行失败: ${error.message}`
      } as any;
    } finally {
      this.isRunning = false;
      this.updateResultArea();
    }
  }

  /**
   * 快速任务（从快捷按钮触发）
   */
  quickTask(task: string): void {
    const input = document.getElementById('ai-command-input') as HTMLTextAreaElement;
    if (input) {
      input.value = task;
    }
    this.executeTask();
  }

  /**
   * 加载历史记录项
   */
  loadHistoryItem(id: string): void {
    const item = this.taskHistory.find(h => h.id === id);
    if (!item) return;

    const input = document.getElementById('ai-command-input') as HTMLTextAreaElement;
    if (input) {
      input.value = item.task;
    }

    this.selectedSkills = [...item.skills];
    this.updateSkillCards();

    if (item.result) {
      this.currentResult = item.result;
      this.updateResultArea();
    }
  }

  /**
   * 清空历史记录
   */
  clearHistory(): void {
    this.taskHistory = [];
    this.saveHistory();
    this.updateResultArea();
  }

  /**
   * 复制结果
   */
  copyResult(): void {
    if (!this.currentResult) return;

    let text = '';
    const final = this.currentResult.final;
    if (final) {
      text = final.summary;
      if (final.recommendations) {
        text += '\n\n建议：\n' + final.recommendations.join('\n');
      }
      if (final.commands) {
        text += '\n\n命令：\n' + final.commands.join('\n');
      }
    } else if (this.currentResult.raw_summary) {
      text = this.currentResult.raw_summary;
    }

    navigator.clipboard.writeText(text).then(() => {
      alert('已复制到剪贴板');
    });
  }

  /**
   * 刷新结果
   */
  refreshResult(): void {
    if (this.currentTask) {
      this.executeTask();
    }
  }

  /**
   * 更新结果区域
   */
  private updateResultArea(): void {
    const resultPanel = document.querySelector('.ai-result-panel');
    if (resultPanel) {
      resultPanel.innerHTML = this.renderResultArea();
    }

    const historyList = document.querySelector('.ai-history-list');
    if (historyList) {
      historyList.innerHTML = this.taskHistory.slice(0, 5).map(item => `
        <div class="ai-history-item" onclick="window.aiCommandCenter?.loadHistoryItem('${item.id}')">
          <span class="ai-step-icon">
            ${item.status === 'completed'
              ? CheckOne({ theme: 'filled', size: '14', fill: 'var(--success-color)' })
              : item.status === 'failed'
                ? CloseOne({ theme: 'filled', size: '14', fill: 'var(--error-color)' })
                : Loading({ theme: 'outline', size: '14', fill: 'var(--primary-color)' })
            }
          </span>
          <span class="ai-history-task">${this.escapeHtml(item.task.substring(0, 40))}${item.task.length > 40 ? '...' : ''}</span>
          <span class="ai-history-time">${this.formatTime(item.timestamp)}</span>
        </div>
      `).join('');
    }
  }

  /**
   * 添加到历史记录
   */
  private addToHistory(item: TaskHistoryItem): void {
    this.taskHistory.unshift(item);
    if (this.taskHistory.length > 20) {
      this.taskHistory = this.taskHistory.slice(0, 20);
    }
    this.saveHistory();
  }

  /**
   * 更新历史记录项
   */
  private updateHistoryItem(item: TaskHistoryItem): void {
    const idx = this.taskHistory.findIndex(h => h.id === item.id);
    if (idx >= 0) {
      this.taskHistory[idx] = item;
      this.saveHistory();
    }
  }

  /**
   * 保存历史记录到 localStorage
   */
  private saveHistory(): void {
    try {
      localStorage.setItem('ai-command-center-history', JSON.stringify(this.taskHistory));
    } catch (error) {
      console.error('保存历史记录失败:', error);
    }
  }

  /**
   * 从 localStorage 加载历史记录
   */
  private loadHistory(): void {
    try {
      const saved = localStorage.getItem('ai-command-center-history');
      if (saved) {
        this.taskHistory = JSON.parse(saved);
      }
    } catch (error) {
      console.error('加载历史记录失败:', error);
      this.taskHistory = [];
    }
  }

  /**
   * 生成唯一 ID
   */
  private generateId(): string {
    return `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * 格式化时间
   */
  private formatTime(timestamp: number): string {
    const now = Date.now();
    const diff = now - timestamp;

    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
    return new Date(timestamp).toLocaleDateString('zh-CN');
  }

  /**
   * 获取状态标签
   */
  private getStatusLabel(status: string): string {
    const labels: Record<string, string> = {
      completed: '完成',
      failed: '失败',
      running: '执行中',
      pending: '等待',
      skipped: '跳过'
    };
    return labels[status] || status;
  }

  /**
   * HTML 转义
   */
  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}

export const aiCommandCenterRenderer = new AICommandCenterRenderer();
