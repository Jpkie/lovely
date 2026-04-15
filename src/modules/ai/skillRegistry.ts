/**
 * Skill 注册表管理
 * 前端 Skill 快捷入口和选择管理
 */

import type { SkillDefinition, SkillShortcut } from './agentTypes';
import { agentService } from './agentService';

// 内置 Skill 快捷入口
export const BUILTIN_SKILL_SHORTCUTS: SkillShortcut[] = [
  {
    id: 'host_triage',
    name: '主机 triage',
    description: '快速评估主机安全状态',
    icon: '🏠',
    keywords: ['主机', '安全', '评估', 'triage', '快速'],
  },
  {
    id: 'log_investigation',
    name: '日志调查',
    description: '深入分析系统日志',
    icon: '📋',
    keywords: ['日志', 'log', '调查', '分析', 'auth'],
  },
  {
    id: 'process_hunt',
    name: '进程狩猎',
    description: '查找可疑进程',
    icon: '🔍',
    keywords: ['进程', 'process', '可疑', '资源'],
  },
  {
    id: 'port_hunt',
    name: '端口狩猎',
    description: '扫描开放端口',
    icon: '🚪',
    keywords: ['端口', 'port', '扫描', '网络'],
  },
  {
    id: 'ssh_audit',
    name: 'SSH 审计',
    description: '审计 SSH 安全配置',
    icon: '🔐',
    keywords: ['ssh', 'sshd', '安全', '审计', '配置'],
  },
  {
    id: 'fix_advisor',
    name: '修复建议',
    description: '基于检测结果的修复建议',
    icon: '💡',
    keywords: ['修复', 'fix', '建议', '整改'],
  },
];

/**
 * Skill 注册表类
 */
export class SkillRegistry {
  private static instance: SkillRegistry;
  private skills: SkillDefinition[] = [];
  private shortcuts: SkillShortcut[] = BUILTIN_SKILL_SHORTCUTS;
  private initialized: boolean = false;

  private constructor() {}

  public static getInstance(): SkillRegistry {
    if (!SkillRegistry.instance) {
      SkillRegistry.instance = new SkillRegistry();
    }
    return SkillRegistry.instance;
  }

  /**
   * 初始化 - 从后端加载 Skills
   */
  public async initialize(): Promise<void> {
    if (this.initialized) return;

    try {
      const result = await agentService.getSkills();
      this.skills = result.skills || [];
      this.initialized = true;
    } catch (error) {
      console.error('Failed to initialize skill registry:', error);
      // 使用内置快捷入口作为后备
      this.skills = [];
    }
  }

  /**
   * 获取所有 Skills
   */
  public getSkills(): SkillDefinition[] {
    return [...this.skills];
  }

  /**
   * 获取 Skill 快捷入口
   */
  public getShortcuts(): SkillShortcut[] {
    return [...this.shortcuts];
  }

  /**
   * 根据 ID 获取 Skill
   */
  public getSkillById(id: string): SkillDefinition | undefined {
    return this.skills.find(s => s.id === id);
  }

  /**
   * 匹配 Skill 快捷入口
   */
  public matchShortcuts(query: string): SkillShortcut[] {
    if (!query) return this.shortcuts;

    const lowerQuery = query.toLowerCase();
    return this.shortcuts.filter(shortcut => {
      if (shortcut.name.toLowerCase().includes(lowerQuery)) return true;
      if (shortcut.description.toLowerCase().includes(lowerQuery)) return true;
      if (shortcut.keywords.some(k => k.toLowerCase().includes(lowerQuery))) return true;
      return false;
    });
  }

  /**
   * 根据任务自动选择合适的 Skills
   */
  public autoSelectSkills(task: string): string[] {
    const matchedShortcuts = this.matchShortcuts(task);
    return matchedShortcuts.slice(0, 3).map(s => s.id);
  }

  /**
   * 获取 Skill 分类
   */
  public getSkillsByCategory(): Record<string, SkillDefinition[]> {
    const categories: Record<string, SkillDefinition[]> = {};

    for (const skill of this.skills) {
      const cat = skill.category || 'other';
      if (!categories[cat]) {
        categories[cat] = [];
      }
      categories[cat].push(skill);
    }

    return categories;
  }

  /**
   * 渲染 Skill 快捷入口 HTML
   */
  public renderSkillShortcuts(selectedSkills: string[] = []): string {
    return this.shortcuts.map(shortcut => {
      const isSelected = selectedSkills.includes(shortcut.id);
      return `
        <button
          class="skill-shortcut-btn ${isSelected ? 'selected' : ''}"
          data-skill-id="${shortcut.id}"
          onclick="window.toggleAgentSkill && window.toggleAgentSkill('${shortcut.id}')"
          style="
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 6px;
            padding: 12px 16px;
            background: ${isSelected ? 'var(--primary-color)22' : 'var(--bg-secondary)'};
            border: 1px solid ${isSelected ? 'var(--primary-color)' : 'var(--border-color)'};
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s;
            min-width: 100px;
          "
          onmouseover="this.style.background = '${isSelected ? 'var(--primary-color)33' : 'var(--bg-tertiary)'}"
          onmouseout="this.style.background = '${isSelected ? 'var(--primary-color)22' : 'var(--bg-secondary)'}'"
        >
          <span style="font-size: 24px;">${shortcut.icon}</span>
          <span style="font-size: 12px; color: var(--text-primary); font-weight: 500;">${shortcut.name}</span>
          <span style="font-size: 11px; color: var(--text-secondary);">${shortcut.description}</span>
        </button>
      `;
    }).join('');
  }

  /**
   * 渲染 Skill 选择列表 HTML
   */
  public renderSkillSelectionList(selectedSkills: string[] = []): string {
    const categories = this.getSkillsByCategory();

    return Object.entries(categories).map(([category, skills]) => `
      <div class="skill-category" style="margin-bottom: 16px;">
        <h4 style="margin: 0 0 8px; font-size: 13px; color: var(--text-secondary); text-transform: uppercase;">${category}</h4>
        <div style="display: flex; flex-wrap: wrap; gap: 8px;">
          ${skills.map(skill => {
            const isSelected = selectedSkills.includes(skill.id);
            return `
              <label style="
                display: flex;
                align-items: center;
                gap: 6px;
                padding: 6px 12px;
                background: ${isSelected ? 'var(--primary-color)22' : 'var(--bg-secondary)'};
                border: 1px solid ${isSelected ? 'var(--primary-color)' : 'var(--border-color)'};
                border-radius: 8px;
                cursor: pointer;
                font-size: 13px;
                color: var(--text-primary);
              ">
                <input
                  type="checkbox"
                  value="${skill.id}"
                  ${isSelected ? 'checked' : ''}
                  onchange="window.toggleAgentSkill && window.toggleAgentSkill('${skill.id}')"
                  style="accent-color: var(--primary-color);"
                />
                ${skill.name}
              </label>
            `;
          }).join('')}
        </div>
      </div>
    `).join('');
  }
}

// 导出单例
export const skillRegistry = SkillRegistry.getInstance();
