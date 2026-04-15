/**
 * 文件右键菜单和安全分析
 */

import { invoke } from '../../shims/@tauri-apps/api/core'
import { marked } from 'marked'

interface CommandHistory {
  timestamp: string
  action: string
  actionName: string
  filePath: string
  fileName: string
  command: string
  result: string
}

export class FileContextMenu {
  private currentFilePath: string = ''
  private currentAnalysisContent: string = ''
  private currentAnalysisTitle: string = ''
  private commandHistory: CommandHistory[] = []

  constructor() {
    // 复用 processContextMenu 的模态框，不需要创建新的
    this.setupEventListeners()
  }

  /**
   * 设置事件监听器
   */
  private setupEventListeners() {
    // AI 解释按钮
    document.addEventListener('click', (e) => {
      const target = e.target as HTMLElement
      if (target.id === 'ai-explain-btn' || target.closest('#ai-explain-btn')) {
        // 检查当前是否是文件分析模态框
        const modal = document.getElementById('process-detail-modal')
        if (modal && modal.style.display === 'flex' && this.currentFilePath) {
          this.explainWithAI()
        }
      }
    })
  }

  /**
   * 显示模态框（复用 processContextMenu 的模态框）
   */
  private showModal(title: string, content: string) {
    const modal = document.getElementById('process-detail-modal')
    const titleEl = document.getElementById('modal-title')
    const contentEl = document.getElementById('modal-content')
    const explanationEl = document.getElementById('ai-explanation')

    if (!modal || !titleEl || !contentEl) {
      console.error('❌ [FileContextMenu] 找不到 processContextMenu 的模态框元素')
      return
    }

    // 设置标题和内容
    titleEl.textContent = title
    contentEl.textContent = content

    // 隐藏AI解释区域（每次显示新内容时重置）
    if (explanationEl) {
      explanationEl.style.display = 'none'
      const explanationContentEl = document.getElementById('ai-explanation-content')
      if (explanationContentEl) {
        explanationContentEl.textContent = ''
      }
    }

    // 显示模态框
    modal.style.display = 'flex'
  }

  /**
   * 执行文件分析命令（使用独立 session）
   */
  private async executeAnalysis(action: string, filePath: string) {
    try {
      const result = await invoke('sftp_file_analysis_independent', {
        action,
        filePath
      }) as any

      // 添加到历史记录
      this.addToHistory(result)

      return result.result as string
    } catch (error) {
      throw new Error(`分析失败: ${error}`)
    }
  }

  /**
   * 添加到历史记录
   */
  private addToHistory(data: any) {
    const actionName = this.getActionName(data.action)
    const fileName = data.file_path.split('/').pop() || data.file_path

    // 保存到历史记录数组
    const historyItem: CommandHistory = {
      timestamp: data.timestamp,
      action: data.action,
      actionName: actionName,
      filePath: data.file_path,
      fileName: fileName,
      command: this.getCommandForAction(data.action, data.file_path),
      result: data.result
    }

    // 插入到数组开头
    this.commandHistory.unshift(historyItem)

    // 限制历史记录数量（最多保留 50 条）
    if (this.commandHistory.length > 50) {
      this.commandHistory.pop()
    }
  }

  /**
   * 获取动作对应的命令
   */
  private getCommandForAction(action: string, filePath: string): string {
    const commands: Record<string, string> = {
      'hash': `md5sum "${filePath}" && sha1sum "${filePath}" && sha256sum "${filePath}"`,
      'signature': `file -b "${filePath}"`,
      'permissions': `ls -lh "${filePath}" && stat -c '%A %a %U:%G' "${filePath}"`,
      'timestamps': `stat "${filePath}"`,
      'inode': `stat -c 'Inode: %i\\nLinks: %h\\nDevice: %d\\nSize: %s bytes' "${filePath}"`,
      'mime-type': `file -b --mime-type "${filePath}"`,
      'file-size': `du -h "${filePath}" && ls -lh "${filePath}"`,
      'strings': `strings -n 8 "${filePath}" | head -100`,
      'hex-dump': `xxd "${filePath}" | head -50`,
      'line-count': `wc -l "${filePath}"`,
      'archive-list': `tar -tzf "${filePath}" 2>/dev/null || unzip -l "${filePath}" 2>/dev/null`,
      'elf-header': `readelf -h "${filePath}"`,
      'processes': `lsof "${filePath}" 2>/dev/null || fuser -v "${filePath}" 2>/dev/null`,
      'package-owner': `dpkg -S "${filePath}" 2>/dev/null || rpm -qf "${filePath}" 2>/dev/null`,
      'hard-links': `find / -samefile "${filePath}" 2>/dev/null`,
      'process-maps': `grep "${filePath}" /proc/*/maps 2>/dev/null`,
      'xattr': `getfattr -d "${filePath}" 2>/dev/null || xattr -l "${filePath}" 2>/dev/null`,
      'capabilities': `getcap "${filePath}"`,
      'selinux-context': `ls -Z "${filePath}"`,
      'dynamic-deps': `ldd "${filePath}" 2>/dev/null`,
      'config-references': `grep -r "${filePath}" /etc/ 2>/dev/null | head -20`,
      'symlink-analysis': `ls -l "${filePath}" && readlink -f "${filePath}"`,
      'suspicious-path': `echo "${filePath}" | grep -E '(/tmp/|/dev/shm/|/var/tmp/|\\.\\.)'`,
      'hidden-file': `basename "${filePath}" | grep '^\\.'`,
      'suid-sgid': `find "${filePath}" -perm /6000 -ls`,
      'webshell': `grep -E '(eval|base64_decode|system|exec|shell_exec|passthru)' "${filePath}"`,
      'backdoor': `grep -E '(nc -e|/bin/bash|/bin/sh.*-i)' "${filePath}"`,
      'crypto-mining': `grep -E '(xmrig|stratum|cryptonight|monero)' "${filePath}"`,
      'reverse-shell': `grep -E '(bash -i|sh -i|nc.*-e|/dev/tcp/)' "${filePath}"`
    }
    return commands[action] || `未知命令: ${action}`
  }

  /**
   * 显示历史记录模态框
   */
  public showHistoryModal() {
    const modal = document.getElementById('process-detail-modal')
    const titleEl = document.getElementById('modal-title')
    const contentEl = document.getElementById('modal-content')
    const explanationEl = document.getElementById('ai-explanation')

    if (!modal || !titleEl || !contentEl || !explanationEl) {
      console.error('模态框元素不存在')
      return
    }

    // 设置标题
    titleEl.textContent = '📜 命令执行历史'

    // 隐藏 AI 解释区域
    explanationEl.style.display = 'none'

    // 生成历史记录 HTML
    let historyHTML = ''

    if (this.commandHistory.length === 0) {
      historyHTML = '<div style="text-align: center; padding: 40px; color: var(--text-tertiary);">暂无历史记录</div>'
    } else {
      historyHTML = `
        <div style="
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
          gap: 8px;
          max-height: 600px;
          overflow-y: auto;
          padding: 2px;
        ">
          ${this.commandHistory.map((item, index) => `
            <div style="
              padding: 4px 6px;
              background: var(--bg-secondary);
              border-radius: 4px;
              border-left: 2px solid var(--primary-color);
              line-height: 1.3;
            ">
              <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 2px;
                padding-bottom: 2px;
                border-bottom: 1px solid var(--border-color);
              ">
                <div style="display: flex; align-items: center; gap: 4px;">
                  <span style="
                    color: var(--text-tertiary);
                    font-size: 10px;
                    background: var(--bg-tertiary);
                    padding: 0px 4px;
                    border-radius: 2px;
                  ">#${this.commandHistory.length - index}</span>
                  <span style="color: var(--primary-color); font-weight: 600; font-size: 12px;">${item.actionName}</span>
                </div>
                <span style="color: var(--text-tertiary); font-size: 10px;">${item.timestamp}</span>
              </div>

              <div style="
                color: var(--text-secondary);
                margin-bottom: 2px;
                font-size: 11px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
              " title="${this.escapeHtml(item.filePath)}">📄 ${item.fileName}</div>

              <details style="margin-bottom: 2px;">
                <summary style="
                  cursor: pointer;
                  color: var(--text-tertiary);
                  font-size: 11px;
                  padding: 0;
                  user-select: none;
                ">💻 命令</summary>
                <div style="
                  font-family: 'Consolas', 'Monaco', monospace;
                  font-size: 11px;
                  padding: 4px;
                  margin-top: 2px;
                  background: var(--bg-tertiary);
                  border-radius: 3px;
                  color: var(--text-primary);
                  overflow-x: auto;
                  white-space: pre-wrap;
                  word-break: break-all;
                  max-height: 80px;
                  overflow-y: auto;
                  line-height: 1.4;
                ">${this.escapeHtml(item.command)}</div>
              </details>

              <details>
                <summary style="
                  cursor: pointer;
                  color: var(--text-tertiary);
                  font-size: 11px;
                  padding: 0;
                  user-select: none;
                ">📋 结果</summary>
                <div style="
                  font-family: 'Consolas', 'Monaco', monospace;
                  font-size: 11px;
                  padding: 4px;
                  margin-top: 2px;
                  background: var(--bg-tertiary);
                  border-radius: 3px;
                  color: var(--text-primary);
                  max-height: 120px;
                  overflow-y: auto;
                  white-space: pre-wrap;
                  word-break: break-all;
                  line-height: 1.4;
                ">${this.escapeHtml(item.result)}</div>
              </details>
            </div>
          `).join('')}
        </div>
      `
    }

    contentEl.innerHTML = historyHTML

    // 显示模态框
    modal.style.display = 'flex'
  }

  /**
   * HTML 转义
   */
  private escapeHtml(text: string): string {
    const div = document.createElement('div')
    div.textContent = text
    return div.innerHTML
  }

  /**
   * 获取动作的中文名称
   */
  private getActionName(action: string): string {
    const actionNames: Record<string, string> = {
      'hash': '哈希值',
      'signature': '文件类型',
      'permissions': '权限',
      'timestamps': '时间戳',
      'inode': 'Inode',
      'mime-type': 'MIME',
      'file-size': '大小',
      'strings': '字符串',
      'hex-dump': 'HEX',
      'line-count': '行数',
      'archive-list': '压缩列表',
      'elf-header': 'ELF头',
      'processes': '进程',
      'package-owner': '所属包',
      'hard-links': '硬链接',
      'process-maps': '内存映射',
      'xattr': '扩展属性',
      'capabilities': '能力',
      'selinux-context': 'SELinux',
      'dynamic-deps': '动态依赖',
      'config-references': '配置引用',
      'symlink-analysis': '符号链接',
      'suspicious-path': '可疑路径',
      'hidden-file': '隐藏文件',
      'suid-sgid': 'SUID/SGID',
      'webshell': 'Webshell',
      'backdoor': '后门',
      'crypto-mining': '挖矿',
      'reverse-shell': '反弹Shell'
    }
    return actionNames[action] || action
  }

  /**
   * 处理菜单项点击
   */
  public async handleAction(action: string, filePath: string) {
    // VIP 功能检查 - 暂时注释掉，后续可以添加
    // const vipActions = [
    //   'webshell-detection',
    //   'backdoor-detection',
    //   'crypto-mining-detection',
    //   'reverse-shell-detection'
    // ]

    this.showModal('正在分析...', '请稍候...')

    try {
      let result: string
      let title: string

      switch (action) {
        case 'file-hash':
          title = '文件哈希值'
          result = await this.executeAnalysis('hash', filePath)
          break
        case 'file-signature':
          title = '文件类型识别'
          result = await this.executeAnalysis('signature', filePath)
          break
        case 'file-size':
          title = '文件大小详情'
          result = await this.executeAnalysis('file-size', filePath)
          break
        case 'file-permissions':
          title = '文件权限分析'
          result = await this.executeAnalysis('permissions', filePath)
          break
        case 'file-timestamps':
          title = '文件时间戳'
          result = await this.executeAnalysis('timestamps', filePath)
          break
        case 'inode':
          title = 'Inode 信息'
          result = await this.executeAnalysis('inode', filePath)
          break
        case 'mime-type':
          title = 'MIME 类型'
          result = await this.executeAnalysis('mime-type', filePath)
          break

        // 内容分析
        case 'file-strings':
          title = '字符串提取'
          result = await this.executeAnalysis('strings', filePath)
          break
        case 'hex-dump':
          title = 'HEX 十六进制'
          result = await this.executeAnalysis('hex-dump', filePath)
          break
        case 'line-count':
          title = '行数统计'
          result = await this.executeAnalysis('line-count', filePath)
          break
        case 'archive-list':
          title = '压缩文件列表'
          result = await this.executeAnalysis('archive-list', filePath)
          break
        case 'elf-header':
          title = 'ELF 头解析'
          result = await this.executeAnalysis('elf-header', filePath)
          break

        // 系统关联
        case 'file-processes':
          title = '关联进程'
          result = await this.executeAnalysis('processes', filePath)
          break
        case 'package-owner':
          title = '所属包查询'
          result = await this.executeAnalysis('package-owner', filePath)
          break
        case 'hard-links':
          title = '硬链接查找'
          result = await this.executeAnalysis('hard-links', filePath)
          break
        case 'process-maps':
          title = '进程内存映射'
          result = await this.executeAnalysis('process-maps', filePath)
          break

        // 元数据与签名
        case 'xattr':
          title = '扩展属性'
          result = await this.executeAnalysis('xattr', filePath)
          break
        case 'capabilities':
          title = '文件能力'
          result = await this.executeAnalysis('capabilities', filePath)
          break
        case 'selinux-context':
          title = 'SELinux 标签'
          result = await this.executeAnalysis('selinux-context', filePath)
          break

        // 文件关系
        case 'dynamic-deps':
          title = '动态依赖分析'
          result = await this.executeAnalysis('dynamic-deps', filePath)
          break
        case 'config-references':
          title = '配置文件引用'
          result = await this.executeAnalysis('config-references', filePath)
          break
        case 'symlink-analysis':
          title = '符号链接分析'
          result = await this.executeAnalysis('symlink-analysis', filePath)
          break
        case 'suspicious-path':
          title = '可疑路径检测'
          result = await this.executeAnalysis('suspicious-path', filePath)
          break
        case 'hidden-file':
          title = '隐藏文件检测'
          result = await this.executeAnalysis('hidden-file', filePath)
          break
        case 'suid-sgid':
          title = 'SUID/SGID 检测'
          result = await this.executeAnalysis('suid-sgid', filePath)
          break
        case 'webshell-detection':
          title = 'Webshell 特征检测'
          result = await this.executeAnalysis('webshell', filePath)
          break
        case 'backdoor-detection':
          title = '后门特征检测'
          result = await this.executeAnalysis('backdoor', filePath)
          break
        case 'crypto-mining-detection':
          title = '挖矿程序检测'
          result = await this.executeAnalysis('crypto-mining', filePath)
          break
        case 'reverse-shell-detection':
          title = '反弹Shell检测'
          result = await this.executeAnalysis('reverse-shell', filePath)
          break
        default:
          result = '未知操作'
          title = '错误'
      }

      // 保存当前分析信息，供 AI 解释使用
      this.currentFilePath = filePath
      this.currentAnalysisTitle = title
      this.currentAnalysisContent = result

      // 更新模态框内容（showModal 会自动隐藏 AI 解释区域）
      this.showModal(title, result)
    } catch (error) {
      this.showModal('错误', `${error}`)
      console.error('文件分析失败:', error)
    }
  }

  /**
   * 使用 AI 解释分析结果（复用 processContextMenu 的 AI 解释区域）
   */
  private async explainWithAI() {
    const explanationEl = document.getElementById('ai-explanation')
    const explanationContentEl = document.getElementById('ai-explanation-content')

    if (!explanationEl || !explanationContentEl) return

    // 显示 AI 解释区域
    explanationEl.style.display = 'block'
    explanationContentEl.textContent = '🤖 正在分析...'

    try {
      // 获取 AI 设置
      const settingsContent = await invoke('read_settings_file') as string
      let settings: any = {}

      if (settingsContent) {
        settings = JSON.parse(settingsContent)
      }

      // 如果后端设置文件没有 AI 配置，使用默认 AI 配置
      if (!settings.ai) {
        settings.ai = {
          currentProvider: 'openai',
          providers: {
            openai: { name: 'OpenAI', baseUrl: 'https://api.openai.com/v1', model: 'gpt-3.5-turbo', apiKey: '' },
            deepseek: { name: 'DeepSeek', baseUrl: 'https://api.deepseek.com/v1', model: 'deepseek-chat', apiKey: '' }
          }
        }
      }

      if (!settings.ai || !settings.ai.currentProvider) {
        throw new Error('AI配置异常，请在设置中配置AI')
      }

      const currentProvider = settings.ai.currentProvider
      const providerConfig = settings.ai.providers[currentProvider]

      if (!providerConfig) {
        throw new Error('AI提供商配置不存在')
      }

      if (!providerConfig.apiKey && currentProvider !== 'ollama') {
        throw new Error('AI API Key 未配置')
      }

      // 构建提示词
      const systemPrompt = `你是一个 Linux 安全专家和应急响应专家。

# 任务
分析以下文件安全分析结果，并提供专业的解释和建议。

# 文件信息
- 文件路径：${this.currentFilePath}
- 分析类型：${this.currentAnalysisTitle}

# 分析结果
${this.currentAnalysisContent}

# 输出要求
请按照以下顺序提供分析：
1. **结果概要**：简要总结分析结果
2. **关键发现**：列出重要的发现和特征
3. **安全评估**：评估潜在的安全风险（如果适用）
4. **建议操作**：提供具体的操作建议（如果适用）

请使用清晰的 Markdown 格式，确保内容结构化、易读。`

      // 清空"正在分析"提示
      explanationContentEl.innerHTML = ''

      // 使用一个变量来累积内容，避免 DOM 更新顺序问题
      let accumulatedContent = ''
      let updateTimer: number | null = null

      // 调用 AI API，使用真正的流式输出
      await this.callAIAPI(systemPrompt, providerConfig, (chunk: string) => {
        // 累积内容
        accumulatedContent += chunk

        // 使用节流更新，避免闪烁（每 100ms 更新一次）
        if (updateTimer) {
          clearTimeout(updateTimer)
        }

        updateTimer = window.setTimeout(() => {
          // 实时更新 UI（使用累积的完整内容，并渲染 Markdown）
          explanationContentEl.innerHTML = this.renderMarkdown(accumulatedContent)
        }, 100)
      })

      // 确保最后一次更新
      if (updateTimer) {
        clearTimeout(updateTimer)
      }
      explanationContentEl.innerHTML = this.renderMarkdown(accumulatedContent)
    } catch (error) {
      explanationContentEl.textContent = `❌ AI解释失败: ${error}\n\n提示：请在设置中配置AI，或者检查AI服务是否可用。`
    }
  }

  /**
   * 调用 AI API（流式输出）
   */
  private async callAIAPI(prompt: string, config: any, onChunk?: (chunk: string) => void): Promise<string> {
    try {
      console.log('🤖 调用AI API (流式模式):', config.name, config.baseUrl)

      // 构建请求体 - 启用流式输出
      const requestBody = {
        model: config.model,
        messages: [
          {
            role: 'system',
            content: prompt
          }
        ],
        temperature: 0.7,
        max_tokens: 1000,
        stream: true  // 启用流式输出
      }

      console.log('📤 AI请求体:', requestBody)

      // 发送请求到 AI API
      const response = await fetch(config.baseUrl + '/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${config.apiKey}`
        },
        body: JSON.stringify(requestBody)
      })

      if (!response.ok) {
        const errorText = await response.text()
        console.error('❌ AI API响应错误:', response.status, errorText)
        throw new Error(`AI API请求失败: ${response.status} ${response.statusText}`)
      }

      // 处理流式响应
      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('无法获取响应流')
      }

      const decoder = new TextDecoder()
      let fullContent = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n').filter(line => line.trim() !== '')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') continue

            try {
              const parsed = JSON.parse(data)
              const content = parsed.choices?.[0]?.delta?.content || ''
              if (content) {
                fullContent += content
                // 调用回调函数，实时更新 UI
                if (onChunk) {
                  onChunk(content)
                }
              }
            } catch (e) {
              console.warn('解析流式数据失败:', e, data)
            }
          }
        }
      }

      console.log('✅ AI生成的解释:', fullContent)
      return fullContent.trim()
    } catch (error) {
      console.error('❌ AI API调用失败:', error)
      throw error
    }
  }

  /**
   * Markdown 渲染器（使用 marked.js）
   */
  private renderMarkdown(markdown: string): string {
    try {
      // 配置 marked
      marked.setOptions({
        breaks: true,  // 支持 GFM 换行
        gfm: true,     // 启用 GitHub Flavored Markdown
      })

      // 渲染 Markdown
      const rawHtml = marked.parse(markdown) as string

      // 添加自定义样式
      const styledHtml = rawHtml
        // 标题样式
        .replace(/<h1>/g, '<h1 style="margin: 18px 0 14px 0; color: var(--primary-color); font-size: 18px; font-weight: 700; line-height: 1.4;">')
        .replace(/<h2>/g, '<h2 style="margin: 16px 0 12px 0; color: var(--primary-color); font-size: 16px; font-weight: 600; line-height: 1.4;">')
        .replace(/<h3>/g, '<h3 style="margin: 14px 0 10px 0; color: var(--text-primary); font-size: 15px; font-weight: 600; line-height: 1.4;">')
        .replace(/<h4>/g, '<h4 style="margin: 12px 0 8px 0; color: var(--text-primary); font-size: 14px; font-weight: 600; line-height: 1.4;">')
        .replace(/<h5>/g, '<h5 style="margin: 10px 0 6px 0; color: var(--text-primary); font-size: 13px; font-weight: 600; line-height: 1.4;">')
        .replace(/<h6>/g, '<h6 style="margin: 8px 0 4px 0; color: var(--text-primary); font-size: 12px; font-weight: 600; line-height: 1.4;">')

        // 段落样式
        .replace(/<p>/g, '<p style="margin: 8px 0; color: var(--text-primary); line-height: 1.6; font-size: 13px;">')

        // 列表样式
        .replace(/<ul>/g, '<ul style="margin: 8px 0; padding-left: 24px; list-style-type: disc;">')
        .replace(/<ol>/g, '<ol style="margin: 8px 0; padding-left: 24px;">')
        .replace(/<li>/g, '<li style="margin: 4px 0; color: var(--text-primary); line-height: 1.5;">')

        // 代码样式
        .replace(/<code>/g, '<code style="background: var(--bg-tertiary); padding: 2px 6px; border-radius: 3px; font-family: \'Consolas\', \'Monaco\', monospace; font-size: 12px; color: var(--primary-color);">')
        .replace(/<pre><code/g, '<pre style="background: var(--bg-tertiary); padding: 12px; border-radius: 6px; overflow-x: auto; margin: 12px 0;"><code style="font-family: \'Consolas\', \'Monaco\', monospace; font-size: 12px; color: var(--text-primary); background: transparent; padding: 0;"')

        // 链接样式
        .replace(/<a /g, '<a style="color: var(--primary-color); text-decoration: underline;" target="_blank" ')

        // 分隔线样式
        .replace(/<hr>/g, '<hr style="border: none; border-top: 1px solid var(--border-color); margin: 16px 0;">')
        .replace(/<hr \/>/g, '<hr style="border: none; border-top: 1px solid var(--border-color); margin: 16px 0;" />')

        // 引用样式
        .replace(/<blockquote>/g, '<blockquote style="margin: 12px 0; padding: 8px 16px; border-left: 4px solid var(--primary-color); background: var(--bg-secondary); color: var(--text-secondary); font-style: italic;">')

        // 表格样式
        .replace(/<table>/g, '<table style="border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 13px;">')
        .replace(/<th>/g, '<th style="border: 1px solid var(--border-color); padding: 8px; background: var(--bg-secondary); color: var(--text-primary); font-weight: 600; text-align: left;">')
        .replace(/<td>/g, '<td style="border: 1px solid var(--border-color); padding: 8px; color: var(--text-primary);">')

        // 粗体和斜体样式
        .replace(/<strong>/g, '<strong style="color: var(--text-primary); font-weight: 600;">')
        .replace(/<em>/g, '<em style="color: var(--text-secondary);">')

      return styledHtml
    } catch (error) {
      console.error('Markdown 渲染失败:', error)
      return markdown
    }
  }
}
