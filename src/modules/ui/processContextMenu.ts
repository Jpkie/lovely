/**
 * 进程右键菜单和详情模态框
 */

import { invoke } from '../../shims/@tauri-apps/api/core'
import * as IconPark from '@icon-park/svg'

export class ProcessContextMenu {
  private contextMenu: HTMLElement | null = null
  private modal: HTMLElement | null = null
  private currentPid: string = ''
  private selectedUsername: string | null = null // 当前选中的账号

  constructor() {
    this.createContextMenu()
    this.createModal()
    this.setupEventListeners()
  }

  /**
   * 创建右键菜单
   */
  private createContextMenu() {
    const menu = document.createElement('div')
    menu.id = 'process-context-menu'
    menu.style.cssText = `
      position: fixed;
      display: none;
      background: var(--bg-secondary);
      border: 1px solid var(--border-color);
      border-radius: var(--border-radius);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      z-index: 10000;
      min-width: 200px;
      padding: var(--spacing-xs) 0;
    `

    menu.innerHTML = `
      <div id="account-selector" class="account-selector" style="
        padding: var(--spacing-sm);
        border-bottom: 1px solid var(--border-color);
        margin-bottom: var(--spacing-xs);
      ">
        <div style="
          display: flex;
          align-items: center;
          gap: var(--spacing-xs);
          font-size: 12px;
          color: var(--text-secondary);
        ">
          <span>${IconPark.User({ theme: 'outline', size: '14', fill: 'currentColor' })}</span>
          <span>执行账号:</span>
          <select id="username-select" style="
            flex: 1;
            padding: 4px 8px;
            border: 1px solid var(--border-color);
            border-radius: var(--border-radius-sm);
            background: var(--bg-tertiary);
            color: var(--text-primary);
            font-size: 12px;
            outline: none;
            cursor: pointer;
          ">
            <option value="">默认账号</option>
          </select>
        </div>
      </div>
      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.FileText({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>基本信息</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="cmdline">
            <span class="menu-label">
              ${IconPark.Terminal({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>命令行参数</span>
            </span>
          </div>
          <div class="menu-item" data-action="exe">
            <span class="menu-label">
              ${IconPark.Application({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>可执行路径</span>
            </span>
          </div>
          <div class="menu-item" data-action="cwd">
            <span class="menu-label">
              ${IconPark.FolderClose({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>当前目录</span>
            </span>
          </div>
        </div>
      </div>
      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.Lock({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>用户与权限</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="status">
            <span class="menu-label">
              ${IconPark.Info({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>进程状态/权限</span>
            </span>
          </div>
          <div class="menu-item" data-action="capabilities">
            <span class="menu-label">
              ${IconPark.Key({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>Capabilities</span>
            </span>
          </div>
          <div class="menu-item" data-action="uid">
            <span class="menu-label">
              ${IconPark.User({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>UID/GID信息</span>
            </span>
          </div>
        </div>
      </div>
      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.FolderOpen({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>文件与内存</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="fd">
            <span class="menu-label">
              ${IconPark.FileCode({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>打开的文件</span>
            </span>
          </div>
          <div class="menu-item" data-action="maps">
            <span class="menu-label">
              ${IconPark.Code({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>动态库/内存映射</span>
            </span>
          </div>
          <div class="menu-item" data-action="limits">
            <span class="menu-label">
              ${IconPark.SettingConfig({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>资源限制</span>
            </span>
          </div>
        </div>
      </div>
      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.NetworkTree({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>网络分析</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="network">
            <span class="menu-label">
              ${IconPark.Connection({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>网络连接</span>
            </span>
          </div>
          <div class="menu-item" data-action="ports">
            <span class="menu-label">
              ${IconPark.PlugOne({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>监听端口</span>
            </span>
          </div>
          <div class="menu-item" data-action="netstat">
            <span class="menu-label">
              ${IconPark.DataDisplay({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>详细网络状态</span>
            </span>
          </div>
          <div class="menu-item" data-action="dns">
            <span class="menu-label">
              ${IconPark.Server({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>DNS查询记录</span>
            </span>
          </div>
        </div>
      </div>
      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.TreeDiagram({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>进程关系</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="pstree">
            <span class="menu-label">
              ${IconPark.Tree({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>父子进程树</span>
            </span>
          </div>
          <div class="menu-item" data-action="children">
            <span class="menu-label">
              ${IconPark.ListBottom({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>子进程列表</span>
            </span>
          </div>
          <div class="menu-item" data-action="parent">
            <span class="menu-label">
              ${IconPark.Up({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>父进程信息</span>
            </span>
          </div>
        </div>
      </div>
      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.ChartPie({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>资源使用</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="io">
            <span class="menu-label">
              ${IconPark.DataSheet({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>I/O 统计</span>
            </span>
          </div>
          <div class="menu-item" data-action="threads">
            <span class="menu-label">
              ${IconPark.ListTwo({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>线程数</span>
            </span>
          </div>
          <div class="menu-item" data-action="memory">
            <span class="menu-label">
              ${IconPark.DatabaseConfig({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>内存使用</span>
            </span>
          </div>
          <div class="menu-item" data-action="cpu">
            <span class="menu-label">
              ${IconPark.Cpu({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>CPU亲和性</span>
            </span>
          </div>
          <div class="menu-item" data-action="cpu-usage">
            <span class="menu-label">
              ${IconPark.ChartLine({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>CPU使用率</span>
            </span>
          </div>
          <div class="menu-item" data-action="context-switches">
            <span class="menu-label">
              ${IconPark.Exchange({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>上下文切换</span>
            </span>
          </div>
          <div class="menu-item" data-action="oom-score">
            <span class="menu-label">
              ${IconPark.Attention({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>OOM分数</span>
            </span>
          </div>
          <div class="menu-item" data-action="scheduler">
            <span class="menu-label">
              ${IconPark.Schedule({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>调度策略</span>
            </span>
          </div>
        </div>
      </div>
      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.Experiment({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>高级分析</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="stack">
            <span class="menu-label">
              ${IconPark.AlignTextBoth({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>调用栈</span>
            </span>
          </div>
          <div class="menu-item" data-action="environ">
            <span class="menu-label">
              ${IconPark.Config({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>环境变量</span>
            </span>
          </div>
          <div class="menu-item" data-action="smaps">
            <span class="menu-label">
              ${IconPark.ChartGraph({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>内存详细信息</span>
            </span>
          </div>
          <div class="menu-item" data-action="syscalls">
            <span class="menu-label">
              ${IconPark.Code({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>系统调用统计</span>
            </span>
          </div>
          <div class="menu-item" data-action="signals">
            <span class="menu-label">
              ${IconPark.Signal({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>信号处理</span>
            </span>
          </div>
          <div class="menu-item" data-action="namespaces">
            <span class="menu-label">
              ${IconPark.Box({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>Namespace信息</span>
            </span>
          </div>
          <div class="menu-item" data-action="cgroup">
            <span class="menu-label">
              ${IconPark.CategoryManagement({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>Cgroup信息</span>
            </span>
          </div>
          <div class="menu-item" data-action="container">
            <span class="menu-label">
              ${IconPark.Application({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>容器检测</span>
            </span>
          </div>
          <div class="menu-item" data-action="uptime">
            <span class="menu-label">
              ${IconPark.Time({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>运行时长</span>
            </span>
          </div>
          <div class="menu-item" data-action="fd-stats">
            <span class="menu-label">
              ${IconPark.ChartHistogram({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>文件描述符统计</span>
            </span>
          </div>
        </div>
      </div>
      <div class="menu-divider"></div>
      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.Protection({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>安全检测</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="suspicious-path">
            <span class="menu-label">
              ${IconPark.FolderFailed({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>可疑路径检测</span>
            </span>
          </div>
          <div class="menu-item" data-action="hidden-process">
            <span class="menu-label">
              ${IconPark.Ghost({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>隐藏进程检测</span>
            </span>
          </div>
          <div class="menu-item" data-action="ld-preload">
            <span class="menu-label">
              ${IconPark.LinkInterrupt({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>LD_PRELOAD检测</span>
            </span>
          </div>
          <div class="menu-item" data-action="deleted-exe">
            <span class="menu-label">
              ${IconPark.Delete({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>已删除可执行文件</span>
            </span>
          </div>
          <div class="menu-item" data-action="suspicious-network">
            <span class="menu-label">
              ${IconPark.LinkCloudFaild({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>可疑网络连接</span>
            </span>
          </div>
          <div class="menu-item" data-action="crypto-mining">
            <span class="menu-label">
              ${IconPark.Bitcoin({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>挖矿特征检测</span>
            </span>
          </div>
        </div>
      </div>
      <div class="menu-divider"></div>
      <div class="menu-item" data-action="kill">
        <span class="menu-label">
          ${IconPark.CloseOne({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>终止进程</span>
        </span>
      </div>
      <div class="menu-item" data-action="kill-9">
        <span class="menu-label">
          ${IconPark.Caution({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>强制终止进程</span>
        </span>
      </div>
    `

    // 添加样式
    const style = document.createElement('style')
    style.textContent = `
      #process-context-menu .menu-item {
        padding: 8px 12px;
        cursor: pointer;
        font-size: 13px;
        color: var(--text-primary);
        transition: background-color 0.2s ease;
        position: relative;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      #process-context-menu .menu-item:hover {
        background: var(--bg-tertiary);
      }
      #process-context-menu .menu-label {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      #process-context-menu .menu-label svg {
        flex-shrink: 0;
      }
      #process-context-menu .menu-parent {
        position: relative;
      }
      #process-context-menu .menu-parent .arrow {
        font-size: 10px;
        color: var(--text-secondary);
        margin-left: 8px;
      }
      #process-context-menu .submenu {
        display: none;
        position: absolute;
        left: 100%;
        top: 0;
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        border-radius: var(--border-radius);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        min-width: 200px;
        z-index: 10001;
      }
      #process-context-menu .menu-parent:hover > .submenu {
        display: block;
      }
      #process-context-menu .submenu .menu-item {
        padding: 8px 16px;
      }
      #process-context-menu .menu-divider {
        height: 1px;
        background: var(--border-color);
        margin: 4px 0;
      }
    `
    document.head.appendChild(style)

    document.body.appendChild(menu)
    this.contextMenu = menu
  }

  /**
   * 创建模态框
   */
  private createModal() {
    const modal = document.createElement('div')
    modal.id = 'process-detail-modal'
    modal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: none;
      align-items: center;
      justify-content: center;
      z-index: 10001;
    `

    modal.innerHTML = `
      <div class="modal-content" style="
        background: var(--bg-primary);
        border-radius: var(--border-radius);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        max-width: 900px;
        max-height: 85vh;
        width: 90%;
        display: flex;
        flex-direction: column;
      ">
        <div class="modal-header" style="
          padding: var(--spacing-md);
          border-bottom: 1px solid var(--border-color);
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: var(--spacing-md);
        ">
          <h3 id="modal-title" style="margin: 0; color: var(--text-primary); font-size: 16px; flex: 1;"></h3>
          <button id="ai-explain-btn" class="modern-btn secondary" style="
            padding: 6px 12px;
            font-size: 13px;
            gap: 6px;
          ">
            ${IconPark.Brain({ theme: 'outline', size: '16', fill: 'currentColor' })}
            <span>AI解释</span>
          </button>
          <button id="modal-close" style="
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: var(--text-secondary);
            padding: 0;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: var(--border-radius-sm);
          ">&times;</button>
        </div>
        <div class="modal-body" style="
          padding: var(--spacing-md);
          overflow-y: auto;
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: var(--spacing-md);
        ">
          <div id="modal-content" style="
            font-family: var(--font-mono);
            font-size: 12px;
            color: var(--text-primary);
            white-space: pre-wrap;
            word-break: break-all;
            padding: var(--spacing-sm);
            background: var(--bg-secondary);
            border-radius: var(--border-radius-sm);
            border: 1px solid var(--border-color);
          "></div>
          <div id="ai-explanation" style="
            display: none;
            padding: var(--spacing-md);
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
            border-radius: var(--border-radius-sm);
            border: 1px solid rgba(102, 126, 234, 0.2);
          ">
            <div style="
              display: flex;
              align-items: center;
              gap: 8px;
              margin-bottom: var(--spacing-sm);
              color: var(--text-primary);
              font-weight: 600;
            ">
              ${IconPark.Brain({ theme: 'outline', size: '18', fill: 'currentColor' })}
              <span>AI解释</span>
            </div>
            <div id="ai-explanation-content" style="
              font-size: 13px;
              line-height: 1.6;
              color: var(--text-primary);
              white-space: pre-wrap;
              word-break: break-word;
            "></div>
          </div>
        </div>
      </div>
    `

    document.body.appendChild(modal)
    this.modal = modal
  }

  /**
   * 设置事件监听器
   */
  private setupEventListeners() {
    // 账号选择器变化事件
    document.addEventListener('change', (e) => {
      const target = e.target as HTMLSelectElement
      if (target.id === 'username-select') {
        this.selectedUsername = target.value || null
        console.log('👤 切换执行账号:', this.selectedUsername || '默认')
      }
    })

    // 鼠标悬停在父菜单项上时，调整二级菜单位置
    this.contextMenu?.querySelectorAll('.menu-parent').forEach(parent => {
      parent.addEventListener('mouseenter', () => {
        const submenu = parent.querySelector('.submenu') as HTMLElement
        if (submenu) {
          // 重置位置
          submenu.style.top = '0'
          submenu.style.bottom = 'auto'

          // 等待submenu显示后再计算位置
          setTimeout(() => {
            const submenuRect = submenu.getBoundingClientRect()
            const windowHeight = window.innerHeight

            // 如果二级菜单底部超出窗口
            if (submenuRect.bottom > windowHeight) {
              // 计算需要向上移动的距离
              const overflow = submenuRect.bottom - windowHeight + 10 // 10px缓冲
              submenu.style.top = `-${overflow}px`

              // 如果向上移动后顶部还是超出窗口，则固定在窗口底部
              const newRect = submenu.getBoundingClientRect()
              if (newRect.top < 0) {
                submenu.style.top = 'auto'
                submenu.style.bottom = '0'
              }
            }
          }, 10)
        }
      })
    })

    // 点击菜单项
    this.contextMenu?.addEventListener('click', (e) => {
      const target = e.target as HTMLElement
      // 查找最近的带有data-action属性的menu-item
      const menuItem = target.closest('.menu-item[data-action]') as HTMLElement
      if (menuItem) {
        const action = menuItem.getAttribute('data-action')
        if (action) {
          console.log(`执行操作: ${action}`)
          this.executeAction(action)
        }
        this.hideContextMenu()
      }
    })

    // 点击模态框外部关闭
    this.modal?.addEventListener('click', (e) => {
      if (e.target === this.modal) {
        this.hideModal()
      }
    })

    // 关闭按钮
    document.getElementById('modal-close')?.addEventListener('click', () => {
      this.hideModal()
    })

    // AI解释按钮
    document.getElementById('ai-explain-btn')?.addEventListener('click', () => {
      this.explainWithAI()
    })

    // 点击其他地方关闭菜单
    document.addEventListener('click', (e) => {
      if (this.contextMenu && this.contextMenu.style.display !== 'none') {
        if (!this.contextMenu.contains(e.target as Node)) {
          this.hideContextMenu()
        }
      }
    })

    // ESC键关闭
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        this.hideContextMenu()
        this.hideModal()
      }
    })
  }

  /**
   * 使用AI解释当前内容
   */
  private async explainWithAI() {

    const contentEl = document.getElementById('modal-content')
    const explanationEl = document.getElementById('ai-explanation')
    const explanationContentEl = document.getElementById('ai-explanation-content')
    const titleEl = document.getElementById('modal-title')

    if (!contentEl || !explanationEl || !explanationContentEl || !titleEl) return

    const content = contentEl.textContent || ''
    const title = titleEl.textContent || ''

    // 显示AI解释区域
    explanationEl.style.display = 'block'
    explanationContentEl.textContent = '🤔 AI正在分析...'

    try {
      // 获取AI设置
      const settingsContent = await invoke('read_settings_file') as string
      let settings: any = {}

      if (settingsContent) {
        settings = JSON.parse(settingsContent)
      }

      // 如果后端设置文件没有AI配置，使用默认AI配置
      if (!settings.ai) {
        settings.ai = {
          currentProvider: 'openai',
          providers: {
            openai: {
              name: 'OpenAI',
              apiKey: '',
              model: 'gpt-3.5-turbo',
              baseUrl: 'https://api.openai.com/v1'
            }
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
        throw new Error('请在设置中配置AI API Key')
      }

      // 构建提示词
      const systemPrompt = `你是一个Linux系统安全专家，擅长分析进程信息、网络连接、系统日志等。请用简洁专业的语言解释用户提供的信息，重点关注安全风险和异常情况。

请分析并解释以下信息：

标题：${title}

内容：
${content}

请提供：
1. 信息概要
2. 关键发现
3. 安全评估（如果适用）
4. 建议操作（如果适用）`

      // 清空"正在分析"提示
      explanationContentEl.textContent = ''

      // 调用AI API，使用真正的流式输出
      await this.callAIAPI(systemPrompt, providerConfig, (chunk: string) => {
        // 实时更新UI
        explanationContentEl.textContent += chunk
      })
    } catch (error) {
      explanationContentEl.textContent = `❌ AI解释失败: ${error}\n\n提示：请在设置中配置AI，或者检查AI服务是否可用。`
    }
  }

  /**
   * 调用AI API（流式输出）
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

      // 发送请求到AI API
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
                // 调用回调函数，实时更新UI
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
   * 显示右键菜单
   */
  public async showContextMenu(x: number, y: number, pid: string) {
    if (!this.contextMenu) return


    this.currentPid = pid

    // 加载当前连接的账号列表
    await this.loadAccountList()

    this.contextMenu.style.left = `${x}px`
    this.contextMenu.style.top = `${y}px`
    this.contextMenu.style.display = 'block'

    // 确保菜单不超出屏幕
    const rect = this.contextMenu.getBoundingClientRect()
    if (rect.right > window.innerWidth) {
      this.contextMenu.style.left = `${window.innerWidth - rect.width - 10}px`
    }
    if (rect.bottom > window.innerHeight) {
      this.contextMenu.style.top = `${window.innerHeight - rect.height - 10}px`
    }
  }

  /**
   * 加载账号列表
   */
  private async loadAccountList() {
    try {
      // 获取当前活动的SSH连接
      const connections = await invoke('load_ssh_connections') as any[]
      if (connections.length === 0) return

      // 假设使用第一个连接的账号列表（在实际应用中，应该获取当前活动连接）
      const connection = connections[0]
      const accounts = connection.accounts || []

      // 更新账号下拉列表
      const select = document.getElementById('username-select') as HTMLSelectElement
      if (!select) return

      // 清空现有选项
      select.innerHTML = '<option value="">默认账号</option>'

      // 添加账号选项
      accounts.forEach((account: any) => {
        const option = document.createElement('option')
        option.value = account.username
        option.textContent = `${account.username}${account.description ? ` (${account.description})` : ''}${account.is_default ? ' [默认]' : ''}`
        select.appendChild(option)
      })

      console.log(`✅ 加载了 ${accounts.length} 个账号`)
    } catch (error) {
      console.error('❌ 加载账号列表失败:', error)
    }
  }

  /**
   * 隐藏右键菜单
   */
  private hideContextMenu() {
    if (this.contextMenu) {
      this.contextMenu.style.display = 'none'
    }
  }

  /**
   * 显示模态框
   */
  private showModal(title: string, content: string) {
    if (!this.modal) return

    const titleEl = document.getElementById('modal-title')
    const contentEl = document.getElementById('modal-content')
    const explanationEl = document.getElementById('ai-explanation')

    if (titleEl) titleEl.textContent = title
    if (contentEl) contentEl.textContent = content

    // 隐藏AI解释区域（每次显示新内容时重置）
    if (explanationEl) {
      explanationEl.style.display = 'none'
      const explanationContentEl = document.getElementById('ai-explanation-content')
      if (explanationContentEl) {
        explanationContentEl.textContent = ''
      }
    }

    this.modal.style.display = 'flex'
  }

  /**
   * 隐藏模态框
   */
  private hideModal() {
    if (this.modal) {
      this.modal.style.display = 'none'

      // 隐藏AI解释区域
      const explanationEl = document.getElementById('ai-explanation')
      if (explanationEl) {
        explanationEl.style.display = 'none'
        const explanationContentEl = document.getElementById('ai-explanation-content')
        if (explanationContentEl) {
          explanationContentEl.textContent = ''
        }
      }
    }
  }

  /**
   * 执行操作
   */
  private async executeAction(action: string) {
    const pid = this.currentPid
    let command = ''
    let title = ''
    let actionName = ''

    switch (action) {
      case 'cmdline':
        command = `cat /proc/${pid}/cmdline | tr '\\0' ' '`
        title = `进程 ${pid} - 命令行参数`
        actionName = '获取命令行参数'
        break
      case 'exe':
        command = `ls -l /proc/${pid}/exe 2>/dev/null || echo "无法访问"`
        title = `进程 ${pid} - 可执行路径`
        actionName = '获取可执行路径'
        break
      case 'cwd':
        command = `ls -l /proc/${pid}/cwd 2>/dev/null || echo "无法访问"`
        title = `进程 ${pid} - 当前目录`
        actionName = '获取当前目录'
        break
      case 'status':
        command = `cat /proc/${pid}/status 2>/dev/null || echo "无法访问"`
        title = `进程 ${pid} - 状态/权限`
        actionName = '获取进程状态'
        break
      case 'capabilities':
        command = `grep Cap /proc/${pid}/status 2>/dev/null || echo "无法访问"`
        title = `进程 ${pid} - Capabilities`
        actionName = '获取Capabilities'
        break
      case 'uid':
        command = `grep -E "^(Uid|Gid|Groups):" /proc/${pid}/status 2>/dev/null || echo "无法访问"`
        title = `进程 ${pid} - UID/GID信息`
        actionName = '获取UID/GID信息'
        break
      case 'fd':
        command = `ls -l /proc/${pid}/fd 2>/dev/null | head -100 || echo "无法访问"`
        title = `进程 ${pid} - 打开的文件（前100个）`
        actionName = '获取打开的文件'
        break
      case 'maps':
        command = `cat /proc/${pid}/maps 2>/dev/null | head -100 || echo "无法访问"`
        title = `进程 ${pid} - 内存映射（前100行）`
        actionName = '获取内存映射'
        break
      case 'limits':
        command = `cat /proc/${pid}/limits 2>/dev/null || echo "无法访问"`
        title = `进程 ${pid} - 资源限制`
        actionName = '获取资源限制'
        break
      case 'network':
        command = `lsof -nP -i -a -p ${pid} 2>/dev/null || (ss -tnp 2>/dev/null | grep "pid=${pid}"; ss -unp 2>/dev/null | grep "pid=${pid}") || echo "无网络连接或权限不足"`
        title = `进程 ${pid} - 网络连接`
        actionName = '获取网络连接'
        break
      case 'ports':
        command = `lsof -nP -i -a -p ${pid} 2>/dev/null | grep LISTEN || ss -tlnp 2>/dev/null | grep "pid=${pid}" || ss -ulnp 2>/dev/null | grep "pid=${pid}" || echo "无监听端口或权限不足"`
        title = `进程 ${pid} - 监听端口`
        actionName = '获取监听端口'
        break
      case 'netstat':
        command = `echo "=== TCP连接 ==="; lsof -nP -i TCP -a -p ${pid} 2>/dev/null || ss -tnp 2>/dev/null | grep "pid=${pid}" || echo "无TCP连接"; echo ""; echo "=== UDP连接 ==="; lsof -nP -i UDP -a -p ${pid} 2>/dev/null || ss -unp 2>/dev/null | grep "pid=${pid}" || echo "无UDP连接"; echo ""; echo "=== 所有网络文件描述符 ==="; ls -l /proc/${pid}/fd 2>/dev/null | grep socket || echo "无socket文件描述符"`
        title = `进程 ${pid} - 详细网络状态`
        actionName = '获取详细网络状态'
        break
      case 'dns':
        command = `lsof -p ${pid} 2>/dev/null | grep -i dns || echo "无DNS查询记录"`
        title = `进程 ${pid} - DNS查询记录`
        actionName = '获取DNS查询记录'
        break
      case 'pstree':
        command = `pstree -p ${pid} 2>/dev/null || echo "pstree命令不可用"`
        title = `进程 ${pid} - 父子进程树`
        actionName = '获取父子进程树'
        break
      case 'children':
        command = `ls /proc/${pid}/task/*/children 2>/dev/null | xargs cat 2>/dev/null || echo "无子进程"`
        title = `进程 ${pid} - 子进程列表`
        actionName = '获取子进程列表'
        break
      case 'parent':
        command = `cat /proc/${pid}/status 2>/dev/null | grep PPid | awk '{print $2}' | xargs -I {} ps -p {} -o pid,user,cmd 2>/dev/null || echo "无法获取父进程"`
        title = `进程 ${pid} - 父进程信息`
        actionName = '获取父进程信息'
        break
      case 'io':
        command = `cat /proc/${pid}/io 2>/dev/null || echo "无法访问"`
        title = `进程 ${pid} - I/O 统计`
        actionName = '获取I/O统计'
        break
      case 'threads':
        command = `ls /proc/${pid}/task 2>/dev/null | wc -l || echo "无法访问"`
        title = `进程 ${pid} - 线程数`
        actionName = '获取线程数'
        break
      case 'memory':
        command = `cat /proc/${pid}/status 2>/dev/null | grep -E "^Vm" || echo "无法访问"`
        title = `进程 ${pid} - 内存使用`
        actionName = '获取内存使用'
        break
      case 'cpu':
        command = `taskset -cp ${pid} 2>/dev/null || echo "无法获取CPU亲和性"`
        title = `进程 ${pid} - CPU亲和性`
        actionName = '获取CPU亲和性'
        break
      case 'stack':
        command = `cat /proc/${pid}/stack 2>/dev/null || echo "无法访问"`
        title = `进程 ${pid} - 调用栈`
        actionName = '获取调用栈'
        break
      case 'environ':
        command = `cat /proc/${pid}/environ 2>/dev/null | tr '\\0' '\\n' || echo "无法访问"`
        title = `进程 ${pid} - 环境变量`
        actionName = '获取环境变量'
        break
      case 'smaps':
        command = `cat /proc/${pid}/smaps 2>/dev/null | head -200 || echo "无法访问"`
        title = `进程 ${pid} - 内存详细信息（前200行）`
        actionName = '获取内存详细信息'
        break

      // 新增功能 - CPU使用率
      case 'cpu-usage':
        command = `echo "=== CPU使用率监控 ==="; echo ""; ps -p ${pid} -o pid,ppid,%cpu,%mem,vsz,rss,tty,stat,start,time,cmd 2>/dev/null || echo "无法获取"; echo ""; echo "=== 实时CPU使用率（5秒采样）==="; for i in {1..5}; do ps -p ${pid} -o %cpu --no-headers 2>/dev/null && sleep 1; done | awk '{sum+=$1; count++} END {if(count>0) print "平均CPU使用率: " sum/count "%"; else print "进程已退出"}'`
        title = `进程 ${pid} - CPU使用率`
        actionName = '获取CPU使用率'
        break

      // 上下文切换
      case 'context-switches':
        command = `echo "=== 上下文切换统计 ==="; echo ""; cat /proc/${pid}/status 2>/dev/null | grep -E "^(voluntary_ctxt_switches|nonvoluntary_ctxt_switches):" || echo "无法访问"; echo ""; echo "说明:"; echo "voluntary_ctxt_switches: 自愿上下文切换（进程主动放弃CPU）"; echo "nonvoluntary_ctxt_switches: 非自愿上下文切换（被调度器强制切换）"`
        title = `进程 ${pid} - 上下文切换`
        actionName = '获取上下文切换统计'
        break

      // OOM分数
      case 'oom-score':
        command = `echo "=== OOM (Out Of Memory) 分数 ==="; echo ""; echo "OOM Score: $(cat /proc/${pid}/oom_score 2>/dev/null || echo '无法访问')"; echo "OOM Score Adj: $(cat /proc/${pid}/oom_score_adj 2>/dev/null || echo '无法访问')"; echo "OOM Adj: $(cat /proc/${pid}/oom_adj 2>/dev/null || echo '无法访问')"; echo ""; echo "说明:"; echo "- OOM Score: 系统计算的OOM分数（0-1000），分数越高越容易被杀死"; echo "- OOM Score Adj: 管理员设置的调整值（-1000到1000）"; echo "- OOM Adj: 旧版本的调整值（-17到15）"; echo ""; echo "当前进程被OOM Killer杀死的可能性: $(cat /proc/${pid}/oom_score 2>/dev/null | awk '{if($1<100) print "低"; else if($1<500) print "中"; else print "高"}' || echo '未知')"`
        title = `进程 ${pid} - OOM分数`
        actionName = '获取OOM分数'
        break

      // 调度策略
      case 'scheduler':
        command = `echo "=== 调度策略和优先级 ==="; echo ""; cat /proc/${pid}/stat 2>/dev/null | awk '{print "调度策略: " $41; print "优先级: " $18; print "Nice值: " $19; print "实时优先级: " $40}' || echo "无法访问"; echo ""; echo "进程状态:"; ps -p ${pid} -o pid,pri,ni,rtprio,sched,stat,wchan:20,cmd 2>/dev/null || echo "无法获取"; echo ""; echo "说明:"; echo "- PRI: 优先级（数值越小优先级越高）"; echo "- NI: Nice值（-20到19，越小优先级越高）"; echo "- RTPRIO: 实时优先级（1-99，仅实时进程）"; echo "- SCHED: 调度策略（TS=普通, FF=FIFO, RR=Round-Robin）"`
        title = `进程 ${pid} - 调度策略`
        actionName = '获取调度策略'
        break

      // 系统调用统计
      case 'syscalls':
        command = `echo "=== 系统调用统计（采样5秒）==="; echo ""; echo "正在采样..."; timeout 5 strace -c -p ${pid} 2>&1 | tail -20 || echo "⚠️ 需要root权限或strace未安装"; echo ""; echo "说明: 显示进程在5秒内执行的系统调用统计"`
        title = `进程 ${pid} - 系统调用统计`
        actionName = '获取系统调用统计'
        break

      // 信号处理
      case 'signals':
        command = `echo "=== 信号处理信息 ==="; echo ""; cat /proc/${pid}/status 2>/dev/null | grep -E "^(Sig|Shd):" || echo "无法访问"; echo ""; echo "说明:"; echo "SigQ: 信号队列"; echo "SigPnd: 待处理信号"; echo "ShdPnd: 共享待处理信号"; echo "SigBlk: 被阻塞的信号"; echo "SigIgn: 被忽略的信号"; echo "SigCgt: 被捕获的信号"`
        title = `进程 ${pid} - 信号处理`
        actionName = '获取信号处理信息'
        break

      // Namespace信息
      case 'namespaces':
        command = `echo "=== Namespace 信息 ==="; echo ""; ls -l /proc/${pid}/ns/ 2>/dev/null || echo "无法访问"; echo ""; echo "=== Namespace 类型说明 ==="; echo "- mnt: 挂载命名空间（文件系统挂载点隔离）"; echo "- uts: UTS命名空间（主机名和域名隔离）"; echo "- ipc: IPC命名空间（进程间通信隔离）"; echo "- pid: PID命名空间（进程ID隔离）"; echo "- net: 网络命名空间（网络栈隔离）"; echo "- user: 用户命名空间（用户和组ID隔离）"; echo "- cgroup: Cgroup命名空间（Cgroup根目录隔离）"`
        title = `进程 ${pid} - Namespace信息`
        actionName = '获取Namespace信息'
        break

      // Cgroup信息
      case 'cgroup':
        command = `echo "=== Cgroup 信息 ==="; echo ""; cat /proc/${pid}/cgroup 2>/dev/null || echo "无法访问"; echo ""; echo "=== Cgroup 资源限制 ==="; cgroup_path=$(cat /proc/${pid}/cgroup 2>/dev/null | head -1 | cut -d: -f3); if [ -n "$cgroup_path" ]; then echo "CPU限制:"; cat /sys/fs/cgroup/cpu$cgroup_path/cpu.cfs_quota_us 2>/dev/null || echo "无限制"; echo "内存限制:"; cat /sys/fs/cgroup/memory$cgroup_path/memory.limit_in_bytes 2>/dev/null | awk '{if($1==9223372036854771712) print "无限制"; else print $1/1024/1024 "MB"}' || echo "无限制"; else echo "未找到cgroup路径"; fi`
        title = `进程 ${pid} - Cgroup信息`
        actionName = '获取Cgroup信息'
        break

      // 容器检测
      case 'container':
        command = `echo "=== 容器环境检测 ==="; echo ""; echo "1. 检查/.dockerenv文件:"; [ -f /.dockerenv ] && echo "✓ 检测到Docker容器" || echo "✗ 未检测到Docker容器"; echo ""; echo "2. 检查cgroup:"; cat /proc/${pid}/cgroup 2>/dev/null | grep -qE "docker|lxc|kubepods" && echo "✓ 检测到容器cgroup" || echo "✗ 未检测到容器cgroup"; echo ""; echo "3. 检查进程namespace:"; ls -l /proc/${pid}/ns/ 2>/dev/null | wc -l | awk '{if($1>4) print "✓ 可能在容器中（多个namespace）"; else print "✗ 可能不在容器中"}'; echo ""; echo "4. 容器类型:"; cat /proc/${pid}/cgroup 2>/dev/null | grep -oE "docker|lxc|kubepods|containerd" | head -1 || echo "未知"`
        title = `进程 ${pid} - 容器检测`
        actionName = '检测容器环境'
        break

      // 运行时长
      case 'uptime':
        command = `echo "=== 进程运行时长 ==="; echo ""; start_time=$(cat /proc/${pid}/stat 2>/dev/null | awk '{print $22}'); system_uptime=$(cat /proc/uptime | awk '{print $1}'); if [ -n "$start_time" ]; then hz=$(getconf CLK_TCK); start_sec=$((start_time / hz)); current_sec=$(echo "$system_uptime" | cut -d. -f1); runtime=$((current_sec - start_sec)); days=$((runtime / 86400)); hours=$(((runtime % 86400) / 3600)); minutes=$(((runtime % 3600) / 60)); seconds=$((runtime % 60)); echo "启动时间: $(ps -p ${pid} -o lstart --no-headers 2>/dev/null)"; echo "运行时长: \${days}天 \${hours}小时 \${minutes}分钟 \${seconds}秒"; echo "总秒数: \${runtime}秒"; else echo "无法获取运行时长"; fi`
        title = `进程 ${pid} - 运行时长`
        actionName = '获取运行时长'
        break

      // 文件描述符统计
      case 'fd-stats':
        command = `echo "=== 文件描述符统计 ==="; echo ""; fd_count=$(ls /proc/${pid}/fd 2>/dev/null | wc -l); fd_limit=$(cat /proc/${pid}/limits 2>/dev/null | grep "Max open files" | awk '{print $4}'); echo "当前打开: $fd_count"; echo "最大限制: $fd_limit"; echo "使用率: $(echo "scale=2; $fd_count * 100 / $fd_limit" | bc 2>/dev/null || echo '无法计算')%"; echo ""; echo "=== 文件描述符类型分布 ==="; for fd in /proc/${pid}/fd/*; do readlink $fd 2>/dev/null; done | awk '{if(/^socket:/) print "socket"; else if(/^pipe:/) print "pipe"; else if(/^anon_inode:/) print "anon_inode"; else if(/^\\//) print "file"; else print "other"}' | sort | uniq -c | sort -rn || echo "无法访问"`
        title = `进程 ${pid} - 文件描述符统计`
        actionName = '获取文件描述符统计'
        break

      case 'suspicious-path':
        command = `exe=$(readlink /proc/${pid}/exe 2>/dev/null); cwd=$(readlink /proc/${pid}/cwd 2>/dev/null); echo "可执行文件: $exe"; echo "工作目录: $cwd"; echo ""; echo "可疑路径检测:"; [[ "$exe" =~ ^(/tmp|/dev/shm|/var/tmp) ]] && echo "⚠️ 可执行文件位于可疑目录: $exe" || echo "✓ 可执行文件路径正常"; [[ "$cwd" =~ ^(/tmp|/dev/shm|/var/tmp) ]] && echo "⚠️ 工作目录位于可疑目录: $cwd" || echo "✓ 工作目录正常"`
        title = `进程 ${pid} - 可疑路径检测`
        actionName = '检测可疑路径'
        break
      case 'hidden-process':
        command = `ps -p ${pid} >/dev/null 2>&1 && echo "✓ 进程在ps中可见" || echo "⚠️ 进程在ps中不可见（可能被隐藏）"; ls -la /proc/${pid} 2>/dev/null | head -5 || echo "⚠️ 无法访问/proc/${pid}"`
        title = `进程 ${pid} - 隐藏进程检测`
        actionName = '检测隐藏进程'
        break
      case 'ld-preload':
        command = `cat /proc/${pid}/environ 2>/dev/null | tr '\\0' '\\n' | grep -E "^(LD_PRELOAD|LD_LIBRARY_PATH)=" && echo "⚠️ 检测到LD_PRELOAD或LD_LIBRARY_PATH" || echo "✓ 未检测到LD_PRELOAD"`
        title = `进程 ${pid} - LD_PRELOAD检测`
        actionName = '检测LD_PRELOAD'
        break
      case 'deleted-exe':
        command = `ls -l /proc/${pid}/exe 2>/dev/null | grep deleted && echo "⚠️ 可执行文件已被删除（可能是恶意进程）" || echo "✓ 可执行文件未被删除"`
        title = `进程 ${pid} - 已删除可执行文件检测`
        actionName = '检测已删除可执行文件'
        break
      case 'suspicious-network':
        command = `echo "网络连接:"; ss -tnp 2>/dev/null | grep "pid=${pid}"; echo ""; echo "可疑连接检测:"; ss -tnp 2>/dev/null | grep "pid=${pid}" | awk '{print $5}' | cut -d: -f1 | sort -u | while read ip; do echo "连接到: $ip"; whois $ip 2>/dev/null | grep -E "^(Country|OrgName):" || echo "无法查询"; done`
        title = `进程 ${pid} - 可疑网络连接检测`
        actionName = '检测可疑网络连接'
        break
      case 'crypto-mining':
        command = `echo "挖矿特征检测:"; echo ""; echo "1. 命令行检测:"; cat /proc/${pid}/cmdline 2>/dev/null | tr '\\0' ' ' | grep -iE "(xmrig|minerd|cpuminer|stratum|pool|mining)" && echo "⚠️ 检测到挖矿关键词" || echo "✓ 未检测到挖矿关键词"; echo ""; echo "2. 网络连接检测:"; ss -tnp 2>/dev/null | grep "pid=${pid}" | grep -E ":(3333|4444|5555|8080|14444)" && echo "⚠️ 检测到常见矿池端口" || echo "✓ 未检测到矿池端口"; echo ""; echo "3. CPU使用率:"; ps -p ${pid} -o %cpu,cmd 2>/dev/null`
        title = `进程 ${pid} - 挖矿特征检测`
        actionName = '检测挖矿特征'
        break
      case 'kill':
        command = `kill ${pid} 2>&1 && echo "✓ 进程已发送终止信号" || echo "✗ 终止失败"`
        title = `进程 ${pid} - 终止进程`
        actionName = '终止进程'
        break
      case 'kill-9':
        command = `kill -9 ${pid} 2>&1 && echo "✓ 进程已强制终止" || echo "✗ 强制终止失败"`
        title = `进程 ${pid} - 强制终止进程`
        actionName = '强制终止进程'
        break
      default:
        console.warn(`未知操作: ${action}`)
        this.showModal('错误', `未知操作: ${action}`)
        return
    }

    // 如果没有设置actionName，使用默认值
    if (!actionName) {
      actionName = '执行命令'
    }

    try {
      // 显示"正在执行"提示
      const userInfo = this.selectedUsername ? ` (用户: ${this.selectedUsername})` : ''
      this.showModal(title, `⏳ 正在执行: ${actionName}${userInfo}...\n\n命令: ${command.substring(0, 100)}${command.length > 100 ? '...' : ''}`)

      // 执行命令，传入选中的账号
      const result = await invoke('ssh_execute_command_direct', {
        command,
        username: this.selectedUsername
      }) as { output: string; exit_code: number }

      // 显示结果
      this.showModal(title, result.output || '✓ 命令执行完成，无输出')
    } catch (error) {
      this.showModal(title, `❌ 执行失败: ${error}`)
    }
  }
}
