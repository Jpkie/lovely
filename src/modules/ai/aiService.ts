/**
 * AI 服务
 * 用于生成安全问题的解决方案
 */

// AI 提供商类型
export type AIProvider = 'openai' | 'deepseek' | 'claude' | 'custom';

// AI 配置接口
export interface AIConfig {
  provider: AIProvider;
  apiKey: string;
  baseUrl?: string; // 自定义 API 端点（用于自托管或代理）
  model?: string; // 模型名称
}

// AI 响应接口
export interface AISolution {
  solution: string;
  steps: string[];
  risks: string[];
  timeEstimate?: string;
}

export interface AIChatMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

/**
 * AI 服务类
 */
export class AIService {
  private static instance: AIService;
  private config: AIConfig | null = null;

  private constructor() {
    this.loadConfigFromStorage();
  }

  /**
   * 获取单例实例
   */
  public static getInstance(): AIService {
    if (!AIService.instance) {
      AIService.instance = new AIService();
    }
    return AIService.instance;
  }

  /**
   * 从本地存储加载配置
   */
  private loadConfigFromStorage(): void {
    try {
      const configStr = localStorage.getItem('lovelyres-ai-config');
      if (configStr) {
        const config = JSON.parse(configStr);
        
        // 验证配置的提供商类型是否有效
        const validProviders: AIProvider[] = ['openai', 'deepseek', 'claude', 'custom'];
        if (config.provider && !validProviders.includes(config.provider)) {
          console.warn('⚠️ 检测到无效的 AI 提供商配置:', config.provider);
          console.warn('⚠️ 已清除无效配置，请重新配置 AI 服务');
          localStorage.removeItem('lovelyres-ai-config');
          this.config = null;
          return;
        }
        
        this.config = config;
      }
    } catch (error) {
      console.error('❌ 加载 AI 配置失败:', error);
      // 清除可能损坏的配置
      localStorage.removeItem('lovelyres-ai-config');
      this.config = null;
    }
  }

  /**
   * 保存配置到本地存储
   */
  public saveConfig(config: AIConfig): void {
    try {
      // 验证配置的提供商类型是否有效
      const validProviders: AIProvider[] = ['openai', 'deepseek', 'claude', 'custom'];
      if (!validProviders.includes(config.provider)) {
        throw new Error(`无效的 AI 提供商类型: ${config.provider}。有效的类型为: ${validProviders.join(', ')}`);
      }
      
      this.config = config;
      localStorage.setItem('lovelyres-ai-config', JSON.stringify(config));
      console.log('✅ AI 配置已保存');
    } catch (error) {
      console.error('❌ 保存 AI 配置失败:', error);
      throw error;
    }
  }

  /**
   * 获取当前配置
   */
  public getConfig(): AIConfig | null {
    return this.config;
  }

  /**
   * 检查是否已配置
   */
  public isConfigured(): boolean {
    return this.config !== null && !!this.config.apiKey;
  }

  /**
   * 清除配置
   */
  public clearConfig(): void {
    this.config = null;
    localStorage.removeItem('lovelyres-ai-config');
  }

  /**
   * 获取 API 端点和请求头
   */
  private getAPIEndpoint(): { url: string; headers: Record<string, string>; model: string } {
    if (!this.config) {
      throw new Error('AI 未配置');
    }

    let url: string;
    let headers: Record<string, string>;
    let model: string;

    switch (this.config.provider) {
      case 'openai':
        url = this.config.baseUrl || 'https://api.openai.com/v1/chat/completions';
        headers = {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.config.apiKey}`,
        };
        model = this.config.model || 'gpt-4o-mini';
        break;

      case 'deepseek':
        url = this.config.baseUrl || 'https://api.deepseek.com/v1/chat/completions';
        headers = {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.config.apiKey}`,
        };
        model = this.config.model || 'deepseek-chat';
        break;

      case 'claude':
        url = this.config.baseUrl || 'https://api.anthropic.com/v1/messages';
        headers = {
          'Content-Type': 'application/json',
          'x-api-key': this.config.apiKey,
          'anthropic-version': '2023-06-01',
        };
        model = this.config.model || 'claude-3-5-sonnet-20241022';
        break;

      case 'custom':
        if (!this.config.baseUrl) {
          throw new Error('自定义提供商需要提供 API 端点');
        }
        url = this.config.baseUrl.trim();
        headers = {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.config.apiKey}`,
        };
        model = this.config.model || 'gpt-4o-mini';
        break;

      default:
        throw new Error(`未知的 AI 提供商: ${this.config.provider}`);
    }

    return { url, headers, model };
  }

  private async requestViaLocalProxy(url: string, headers: Record<string, string>, body: Record<string, any>): Promise<any> {
    const callProxy = async (targetUrl: string): Promise<any> => {
      const resp = await fetch('/api/v1/ai/chat-proxy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: targetUrl,
          headers,
          body,
          timeout_seconds: 90,
        }),
      });

      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) {
        const detail = data?.detail || data?.message || `HTTP ${resp.status}`;
        throw new Error(String(detail));
      }
      return data?.data ?? data;
    };

    try {
      return await callProxy(url);
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      // 保持用户原始 URL 不变；仅在 404 时做兼容重试
      if (!msg.includes('404')) throw error;

      const normalized = url.replace(/\/+$/, '');
      const retryCandidates = [
        `${normalized}/chat/completions`,
        `${normalized}/v3/chat/completions`,
        `${normalized}/api/v3/chat/completions`,
      ];

      for (const candidate of retryCandidates) {
        if (candidate === normalized) continue;
        try {
          return await callProxy(candidate);
        } catch (retryError) {
          const retryMsg = retryError instanceof Error ? retryError.message : String(retryError);
          if (!retryMsg.includes('404')) throw retryError;
        }
      }

      throw error;
    }
  }

  private extractTextFromResponse(responseData: any): string {
    return (
      responseData?.choices?.[0]?.message?.content ||
      responseData?.choices?.[0]?.delta?.content ||
      responseData?.content?.[0]?.text ||
      ''
    );
  }

  /**
   * 生成解决方案
   */
  public async generateSolution(
    title: string,
    description: string,
    severity: string,
    serverInfo?: string
  ): Promise<AISolution> {
    if (!this.isConfigured()) {
      throw new Error('请先配置 AI 服务（设置 -> AI 配置）');
    }

    const { url, headers, model } = this.getAPIEndpoint();

    // 构建提示词
    const systemPrompt = `你是一位资深的 Linux 系统安全专家和运维工程师。你的任务是为用户提供清晰、可执行的安全问题解决方案。

请遵循以下要求：
1. 提供具体的解决步骤，包含完整的命令
2. 解释每个步骤的作用
3. 指出潜在的风险和注意事项
4. 估算解决时间
5. 使用中文回答
6. 回答要专业、准确、实用`;

    const userPrompt = `我在服务器上检测到以下安全问题：

**问题标题**: ${title}
**严重程度**: ${severity}
**问题描述**: ${description}
${serverInfo ? `**服务器信息**: ${serverInfo}` : ''}

请提供详细的解决方案，包括：
1. 问题分析
2. 解决步骤（带命令）
3. 风险提示
4. 预计耗时

请以结构化的格式回答，便于阅读和执行。`;

    try {
      let responseData: any;

      if (this.config!.provider === 'claude') {
        responseData = await this.requestViaLocalProxy(url, headers, {
          model,
          max_tokens: 2048,
          messages: [
            {
              role: 'user',
              content: `${systemPrompt}\n\n${userPrompt}`,
            },
          ],
        });
        const content = this.extractTextFromResponse(responseData);
        return this.parseSolution(content);
      } else {
        responseData = await this.requestViaLocalProxy(url, headers, {
          model,
          messages: [
            {
              role: 'system',
              content: systemPrompt,
            },
            {
              role: 'user',
              content: userPrompt,
            },
          ],
          temperature: 0.7,
          max_tokens: 2048,
        });
        const content = this.extractTextFromResponse(responseData);
        return this.parseSolution(content);
      }
    } catch (error) {
      console.error('❌ AI 解决方案生成失败:', error);
      throw error;
    }
  }

  /**
   * 流式生成简洁解决方案
   */
  public async generateConciseSolutionStream(
    title: string,
    description: string,
    severity: string,
    serverInfo?: string,
    onChunk?: (text: string) => void,
    onComplete?: (fullText: string) => void
  ): Promise<void> {
    if (!this.isConfigured()) {
      throw new Error('请先配置 AI 服务（设置 -> AI 配置）');
    }

    const { url, headers, model } = this.getAPIEndpoint();

    // 构建简洁提示词
    const systemPrompt = `你是一位资深的 Linux 系统安全专家。请提供简洁、可执行的解决方案。

格式要求：
1. 每个步骤简短说明（不超过2句话）
2. 命令格式严格遵循：
   - 每个命令单独一行，用 \`\`\` 包裹
   - 只包含完整的、可直接执行的命令
   - 不要包含命令提示符（如 $、# 等）
   - 不要包含注释或解释
   - 一个代码块只包含一条命令

示例格式：
步骤1：检查当前用户权限
\`\`\`
whoami
\`\`\`

步骤2：查看文件权限
\`\`\`
ls -la /etc/passwd
\`\`\`

3. 总字数控制在300字以内
4. 使用中文描述，命令使用英文`;

    const userPrompt = `安全问题：${title}
严重程度：${severity}
描述：${description}
${serverInfo ? `服务器：${serverInfo}` : ''}

请按照格式要求给出简洁的解决步骤（包含可执行的命令）：`;

    try {
      const responseData = await this.requestViaLocalProxy(url, headers, this.config!.provider === 'claude'
        ? {
            model,
            max_tokens: 500,
            messages: [{ role: 'user', content: `${systemPrompt}\n\n${userPrompt}` }],
          }
        : {
            model,
            messages: [
              { role: 'system', content: systemPrompt },
              { role: 'user', content: userPrompt },
            ],
            temperature: 0.7,
            max_tokens: 500,
          }
      );
      const fullText = this.extractTextFromResponse(responseData);
      if (fullText) onChunk?.(fullText);
      onComplete?.(fullText);
    } catch (error) {
      console.error('❌ AI 流式生成失败:', error);
      throw error;
    }
  }

  /**
   * 流式解释系统日志
   */
  public async explainLogStream(
    logContent: string,
    context?: string,
    onChunk?: (text: string) => void,
    onComplete?: (fullText: string) => void
  ): Promise<void> {
    if (!this.isConfigured()) {
      throw new Error('请先配置 AI 服务（设置 -> AI 配置）');
    }

    const { url, headers, model } = this.getAPIEndpoint();

    const systemPrompt = `你是一位资深的 Linux 系统日志分析专家。请解释用户提供的系统日志。
1. 解释日志的含义，发生了什么事件。
2. 分析日志级别（如 Error, Warning）及其严重性。
3. 如果是错误或警告，给出可能的原因和排查建议。
4. 使用中文回答，保持简洁专业。`;

    const userPrompt = `请解释这条系统日志：
${logContent}
${context ? `\n上下文信息：${context}` : ''}`;

    try {
      const requestBody = {
        model,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt },
        ],
        temperature: 0.7,
        max_tokens: 1000,
      };
      const responseData = await this.requestViaLocalProxy(url, headers, requestBody);
      const fullText = this.extractTextFromResponse(responseData);
      if (fullText) onChunk?.(fullText);
      onComplete?.(fullText);
    } catch (error) {
      console.error('❌ AI 日志解释失败:', error);
      throw error;
    }
  }

  /**
   * 通用聊天（流式）
   */
  public async chatStream(
    messages: AIChatMessage[],
    onChunk?: (text: string) => void,
    onComplete?: (fullText: string) => void
  ): Promise<void> {
    if (!this.isConfigured()) {
      throw new Error('请先配置 AI 服务（设置 -> AI 配置）');
    }

    const { url, headers, model } = this.getAPIEndpoint();

    try {
      let requestBody: any;

      if (this.config!.provider === 'claude') {
        const prompt = messages.map(m => `${m.role}: ${m.content}`).join('\n');
        requestBody = {
          model,
          max_tokens: 2048,
          messages: [{ role: 'user', content: prompt }],
        };
      } else {
        requestBody = {
          model,
          messages,
          temperature: 0.7,
          max_tokens: 2048,
        };
      }
      const responseData = await this.requestViaLocalProxy(url, headers, requestBody);
      const fullText = this.extractTextFromResponse(responseData);
      if (fullText) onChunk?.(fullText);
      onComplete?.(fullText);
    } catch (error) {
      console.error('❌ AI 聊天失败:', error);
      throw error;
    }
  }

  /**
   * 解析 AI 返回的解决方案
   */
  private parseSolution(content: string): AISolution {
    // 提取步骤
    const steps: string[] = [];
    const stepsMatch = content.match(/(?:解决步骤|步骤|操作步骤)[:：]([\s\S]*?)(?=##|风险|注意|预计|$)/i);
    if (stepsMatch) {
      const stepsText = stepsMatch[1];
      const stepMatches = stepsText.matchAll(/(?:^|\n)\s*(?:\d+[\.\、]|[-*])\s*(.+?)(?=\n\s*(?:\d+[\.\、]|[-*])|$)/gs);
      for (const match of stepMatches) {
        const step = match[1].trim();
        if (step) {
          steps.push(step);
        }
      }
    }

    // 提取风险
    const risks: string[] = [];
    const risksMatch = content.match(/(?:风险|注意事项|注意)[:：]([\s\S]*?)(?=##|预计|$)/i);
    if (risksMatch) {
      const risksText = risksMatch[1];
      const riskMatches = risksText.matchAll(/(?:^|\n)\s*(?:\d+[\.\、]|[-*])\s*(.+?)(?=\n\s*(?:\d+[\.\、]|[-*])|$)/gs);
      for (const match of riskMatches) {
        const risk = match[1].trim();
        if (risk) {
          risks.push(risk);
        }
      }
    }

    // 提取时间估算
    const timeMatch = content.match(/(?:预计|耗时|时间)[:：\s]*(.+?)(?:\n|$)/i);
    const timeEstimate = timeMatch ? timeMatch[1].trim() : undefined;

    return {
      solution: content,
      steps: steps.length > 0 ? steps : ['请参考完整解决方案'],
      risks: risks.length > 0 ? risks : ['请仔细阅读完整方案中的注意事项'],
      timeEstimate,
    };
  }

  /**
   * 批量生成解决方案
   */
  public async generateBatchSolutions(
    problems: Array<{
      title: string;
      description: string;
      severity: string;
    }>,
    serverInfo?: string,
    onProgress?: (current: number, total: number) => void
  ): Promise<Map<string, AISolution>> {
    const solutions = new Map<string, AISolution>();

    for (let i = 0; i < problems.length; i++) {
      const problem = problems[i];
      if (onProgress) {
        onProgress(i + 1, problems.length);
      }

      try {
        const solution = await this.generateSolution(
          problem.title,
          problem.description,
          problem.severity,
          serverInfo
        );
        solutions.set(problem.title, solution);

        // 添加延迟避免 API 限流
        if (i < problems.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      } catch (error) {
        console.error(`生成解决方案失败: ${problem.title}`, error);
        // 继续处理下一个
      }
    }

    return solutions;
  }

  /**
   * 测试 API 连接
   */
  public async testConnection(): Promise<boolean> {
    try {
      await this.generateSolution(
        '测试问题',
        '这是一个测试',
        'low'
      );
      return true;
    } catch (error) {
      console.error('AI API 连接测试失败:', error);
      return false;
    }
  }
}

// 导出单例实例
export const aiService = AIService.getInstance();
