/**
 * AI 任务路由器
 * 基于规则的自然语言意图映射到技能
 */

import { BUILTIN_SKILL_SHORTCUTS } from './skillRegistry';

export interface IntentRule {
  patterns: RegExp[];
  skillId: string;
  confidence: 'high' | 'medium' | 'low';
  reason?: string;
}

export class AITaskRouter {
  private static instance: AITaskRouter;

  private rules: IntentRule[] = [
    {
      patterns: [
        /体检|安全检查|主机检查|快速检查|系统检查/,
        /check.*security|security.*check|host.*triage|triage/gi,
        /安全评估|安全巡检/
      ],
      skillId: 'host_triage',
      confidence: 'high',
      reason: '检测到安全检查类关键词'
    },
    {
      patterns: [
        /日志|log|auth\.log|syslog|journal|异常登录|登录失败|登录日志|登录记录/,
        /登录.*分析|分析.*登录|查看.*日志|审计.*日志/,
        /investigation|log.*analysis/gi
      ],
      skillId: 'log_investigation',
      confidence: 'high',
      reason: '检测到日志分析类关键词'
    },
    {
      patterns: [
        /进程|process|木马|可疑进程|隐藏进程|异常进程/,
        /进程.*分析|分析.*进程|查找.*进程|检查.*进程/,
        /process.*hunt|hunt.*process/gi
      ],
      skillId: 'process_hunt',
      confidence: 'high',
      reason: '检测到进程分析类关键词'
    },
    {
      patterns: [
        /端口|port|开放端口|监听端口|端口扫描|网络连接/,
        /端口.*检查|检查.*端口|扫描.*端口/,
        /port.*hunt|hunt.*port|scan.*port/gi
      ],
      skillId: 'port_hunt',
      confidence: 'high',
      reason: '检测到端口扫描类关键词'
    },
    {
      patterns: [
        /ssh|sshd|root.*登录|ssh.*配置|ssh.*安全|ssh.*审计/,
        /ssh.*key|密钥.*ssh|authorized.*key/,
        /ssh.*audit|audit.*ssh/gi
      ],
      skillId: 'ssh_audit',
      confidence: 'high',
      reason: '检测到 SSH 审计类关键词'
    },
    {
      patterns: [
        /修复|整改|建议|加固|修复.*建议|安全.*修复|漏洞.*修复/,
        /fix|remediation|repair|hardening/gi
      ],
      skillId: 'fix_advisor',
      confidence: 'high',
      reason: '检测到修复建议类关键词'
    },
    {
      patterns: [
        /自动修复|一键修复|自动.*修复|ai.*修复|智能修复/,
        /auto.*fix|auto.*remediation|auto.*repair/gi
      ],
      skillId: 'auto_remediation',
      confidence: 'high',
      reason: '检测到自动修复类关键词'
    },
    {
      patterns: [
        /能力检测|功能检测|服务.*检测|服务.*能力|capability.*check/,
        /检测.*能力|检查.*能力/gi
      ],
      skillId: 'capability_check',
      confidence: 'high',
      reason: '检测到能力检测类关键词'
    },
    {
      patterns: [
        /安全基线|基线检查|baseline|安全.*配置|配置.*核查/,
        /hardening.*baseline|baseline.*check/gi
      ],
      skillId: 'hardening_baseline',
      confidence: 'high',
      reason: '检测到安全基线类关键词'
    },
    {
      patterns: [
        /时间线|timeline|事件.*时间|incident.*timeline|安全.*事件.*时间/,
        /timeline.*analysis/gi
      ],
      skillId: 'incident_timeline',
      confidence: 'high',
      reason: '检测到事件时间线类关键词'
    },
    {
      patterns: [
        /安全.*配置|配置.*补丁|patch|补丁.*修复/,
        /safe.*config.*patch|config.*patch/gi
      ],
      skillId: 'safe_config_patch',
      confidence: 'high',
      reason: '检测到配置补丁类关键词'
    },
    {
      patterns: [
        /验证|验证.*修复|验证.*结果|verification|verify.*fix/,
        /remediation.*verification|验证.*修复.*结果/gi
      ],
      skillId: 'remediation_verification',
      confidence: 'high',
      reason: '检测到验证类关键词'
    }
  ];

  private constructor() {}

  public static getInstance(): AITaskRouter {
    if (!AITaskRouter.instance) {
      AITaskRouter.instance = new AITaskRouter();
    }
    return AITaskRouter.instance;
  }

  /**
   * 分析用户输入，返回匹配的技能列表
   * @param userInput 用户输入的自然语言任务描述
   * @returns 匹配的技能 ID 列表，按置信度排序
   */
  public route(userInput: string): { skillId: string; confidence: string; reason?: string }[] {
    if (!userInput || userInput.trim().length === 0) {
      return [];
    }

    const results: { skillId: string; confidence: string; reason?: string }[] = [];

    for (const rule of this.rules) {
      for (const pattern of rule.patterns) {
        if (pattern.test(userInput)) {
          results.push({
            skillId: rule.skillId,
            confidence: rule.confidence,
            reason: rule.reason
          });
          break;
        }
      }
    }

    const confidenceOrder = { high: 0, medium: 1, low: 2 };
    results.sort((a, b) => confidenceOrder[a.confidence as keyof typeof confidenceOrder] - confidenceOrder[b.confidence as keyof typeof confidenceOrder]);

    const uniqueResults: { skillId: string; confidence: string; reason?: string }[] = [];
    const seenSkills = new Set<string>();
    for (const result of results) {
      if (!seenSkills.has(result.skillId)) {
        seenSkills.add(result.skillId);
        uniqueResults.push(result);
      }
    }

    return uniqueResults;
  }

  /**
   * 获取最高置信度的技能
   */
  public routeTop(userInput: string): string | null {
    const results = this.route(userInput);
    return results.length > 0 ? results[0].skillId : null;
  }

  /**
   * 添加自定义规则
   */
  public addRule(rule: IntentRule): void {
    this.rules.push(rule);
  }

  /**
   * 获取所有可用的技能
   */
  public getAvailableSkills(): string[] {
    return BUILTIN_SKILL_SHORTCUTS.map(s => s.id);
  }

  /**
   * 根据技能 ID 获取技能信息
   */
  public getSkillInfo(skillId: string): { id: string; name: string; description: string; icon: string } | null {
    const skill = BUILTIN_SKILL_SHORTCUTS.find(s => s.id === skillId);
    if (skill) {
      return {
        id: skill.id,
        name: skill.name,
        description: skill.description,
        icon: skill.icon
      };
    }
    return null;
  }
}

export const aiTaskRouter = AITaskRouter.getInstance();