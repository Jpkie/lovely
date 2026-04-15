import { invoke } from '../../shims/@tauri-apps/api/core'
import * as IconPark from '@icon-park/svg'

/**
 * 系统服务右键菜单管理器
 */
export class ServiceContextMenu {
  private contextMenu: HTMLElement | null = null
  private modal: HTMLElement | null = null
  private currentService: string = ''
  private selectedUsername: string = ''
  private accounts: any[] = []

  constructor() {
    this.createContextMenu()
    this.createModal()
    this.setupEventListeners()
    this.loadAccountList()
  }

  /**
   * 创建右键菜单
   */
  private createContextMenu() {
    const menu = document.createElement('div')
    menu.id = 'service-context-menu'
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
      <div class="menu-account-selector" style="
        padding: 8px 12px;
        border-bottom: 1px solid var(--border-color);
        background: var(--bg-tertiary);
      ">
        <label style="
          display: block;
          font-size: 11px;
          color: var(--text-secondary);
          margin-bottom: 4px;
        ">执行账号:</label>
        <select id="service-account-select" style="
          width: 100%;
          padding: 4px 8px;
          background: var(--bg-secondary);
          border: 1px solid var(--border-color);
          border-radius: 4px;
          color: var(--text-primary);
          font-size: 12px;
          outline: none;
          cursor: pointer;
        ">
          <option value="">默认账号</option>
        </select>
      </div>

      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.Info({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>基本信息</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="status">
            <span class="menu-label">
              ${IconPark.CheckOne({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>服务状态</span>
            </span>
          </div>
          <div class="menu-item" data-action="config">
            <span class="menu-label">
              ${IconPark.FileText({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看配置文件</span>
            </span>
          </div>
          <div class="menu-item" data-action="details">
            <span class="menu-label">
              ${IconPark.FileSearch({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>服务详细信息</span>
            </span>
          </div>
          <div class="menu-item" data-action="copy-name">
            <span class="menu-label">
              ${IconPark.Copy({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>复制服务名称</span>
            </span>
          </div>
        </div>
      </div>

      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.Power({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>服务控制</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="start">
            <span class="menu-label">
              ${IconPark.Play({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>启动服务</span>
            </span>
          </div>
          <div class="menu-item" data-action="stop">
            <span class="menu-label">
              ${IconPark.Pause({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>停止服务</span>
            </span>
          </div>
          <div class="menu-item" data-action="restart">
            <span class="menu-label">
              ${IconPark.Refresh({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>重启服务</span>
            </span>
          </div>
          <div class="menu-item" data-action="reload">
            <span class="menu-label">
              ${IconPark.Redo({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>重新加载配置</span>
            </span>
          </div>
          <div class="menu-item" data-action="enable">
            <span class="menu-label">
              ${IconPark.Check({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>启用开机自启</span>
            </span>
          </div>
          <div class="menu-item" data-action="disable">
            <span class="menu-label">
              ${IconPark.Close({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>禁用开机自启</span>
            </span>
          </div>
        </div>
      </div>

      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.Log({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>日志查询</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="logs">
            <span class="menu-label">
              ${IconPark.FileText({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看服务日志</span>
            </span>
          </div>
          <div class="menu-item" data-action="errors">
            <span class="menu-label">
              ${IconPark.Caution({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看错误日志</span>
            </span>
          </div>
          <div class="menu-item" data-action="live-logs">
            <span class="menu-label">
              ${IconPark.Connection({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看实时日志</span>
            </span>
          </div>
        </div>
      </div>

      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.NetworkTree({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>依赖分析</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="dependencies">
            <span class="menu-label">
              ${IconPark.Connection({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看依赖服务</span>
            </span>
          </div>
          <div class="menu-item" data-action="reverse-dependencies">
            <span class="menu-label">
              ${IconPark.Return({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看被依赖服务</span>
            </span>
          </div>
          <div class="menu-item" data-action="service-tree">
            <span class="menu-label">
              ${IconPark.Tree({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看服务树</span>
            </span>
          </div>
        </div>
      </div>

      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.ChartPie({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>资源监控</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="cpu-usage">
            <span class="menu-label">
              ${IconPark.Cpu({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>CPU使用率</span>
            </span>
          </div>
          <div class="menu-item" data-action="memory-usage">
            <span class="menu-label">
              ${IconPark.DatabaseConfig({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>内存使用</span>
            </span>
          </div>
          <div class="menu-item" data-action="process-list">
            <span class="menu-label">
              ${IconPark.ListTwo({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>进程列表</span>
            </span>
          </div>
          <div class="menu-item" data-action="open-files">
            <span class="menu-label">
              ${IconPark.FileCode({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>打开的文件</span>
            </span>
          </div>
        </div>
      </div>

      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.Protection({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>安全分析</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="run-user">
            <span class="menu-label">
              ${IconPark.User({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看运行用户</span>
            </span>
          </div>
          <div class="menu-item" data-action="permissions">
            <span class="menu-label">
              ${IconPark.Lock({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看权限配置</span>
            </span>
          </div>
          <div class="menu-item" data-action="security-check">
            <span class="menu-label">
              ${IconPark.Shield({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>配置安全性检查</span>
            </span>
          </div>
        </div>
      </div>

      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.SettingConfig({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>高级操作</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="edit-service">
            <span class="menu-label">
              ${IconPark.Edit({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看服务文件</span>
            </span>
          </div>
          <div class="menu-item" data-action="timer">
            <span class="menu-label">
              ${IconPark.Timer({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看定时器配置</span>
            </span>
          </div>
          <div class="menu-item" data-action="environment">
            <span class="menu-label">
              ${IconPark.Config({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看环境变量</span>
            </span>
          </div>
        </div>
      </div>
    `

    // 添加样式
    const style = document.createElement('style')
    style.textContent = `
      #service-context-menu .menu-item {
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
      #service-context-menu .menu-item:hover {
        background: var(--bg-tertiary);
      }
      #service-context-menu .menu-label {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      #service-context-menu .menu-label svg {
        flex-shrink: 0;
      }
      #service-context-menu .menu-parent {
        position: relative;
      }
      #service-context-menu .menu-parent .arrow {
        font-size: 10px;
        color: var(--text-secondary);
        margin-left: 8px;
      }
      #service-context-menu .submenu {
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
      #service-context-menu .menu-parent:hover > .submenu {
        display: block;
      }
      #service-context-menu .submenu .menu-item {
        padding: 8px 16px;
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
    modal.id = 'service-detail-modal'
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
          <h3 id="service-modal-title" style="margin: 0; color: var(--text-primary); font-size: 16px; flex: 1;"></h3>
          <button id="service-ai-explain-btn" class="modern-btn secondary" style="
            padding: 6px 12px;
            font-size: 13px;
            gap: 6px;
          ">
            ${IconPark.Brain({ theme: 'outline', size: '16', fill: 'currentColor' })}
            <span>AI解释</span>
          </button>
          <button id="service-modal-close" style="
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
          <div id="service-modal-content" style="
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
          <div id="service-ai-explanation" style="
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
            <div id="service-ai-explanation-content" style="
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
   * 加载账号列表
   */
  private async loadAccountList() {
    try {
      const connections = await invoke('load_ssh_connections') as any[]
      if (connections.length === 0) {
        console.log('📋 没有可用的SSH连接')
        return
      }

      const connection = connections[0]
      this.accounts = connection.accounts || []

      const select = document.getElementById('service-account-select') as HTMLSelectElement
      if (!select) {
        console.warn('⚠️ 服务账号选择下拉框未找到')
        return
      }

      select.innerHTML = '<option value="">默认账号</option>'

      this.accounts.forEach((account: any) => {
        const option = document.createElement('option')
        option.value = account.username
        option.textContent = `${account.username}${account.description ? ` (${account.description})` : ''}${account.is_default ? ' [默认]' : ''}`
        select.appendChild(option)
      })

      //console.log(`✅ 服务右键菜单加载了 ${this.accounts.length} 个账号`)
    } catch (error) {
      console.error('❌ 服务右键菜单加载账号列表失败:', error)
    }
  }

  /**
   * 设置事件监听器
   */
  private setupEventListeners() {
    // 账号选择下拉框change事件
    document.addEventListener('change', (e) => {
      const target = e.target as HTMLElement
      if (target.id === 'service-account-select') {
        const select = target as HTMLSelectElement
        this.selectedUsername = select.value
        console.log('👤 服务菜单选择账号:', this.selectedUsername || '默认账号')
      }
    })

    // 鼠标悬停在父菜单项上时，调整二级菜单位置
    this.contextMenu?.querySelectorAll('.menu-parent').forEach(parent => {
      parent.addEventListener('mouseenter', () => {
        const submenu = parent.querySelector('.submenu') as HTMLElement
        if (submenu) {
          submenu.style.top = '0'
          submenu.style.bottom = 'auto'

          setTimeout(() => {
            const submenuRect = submenu.getBoundingClientRect()
            const windowHeight = window.innerHeight

            if (submenuRect.bottom > windowHeight) {
              const overflow = submenuRect.bottom - windowHeight + 10
              submenu.style.top = `-${overflow}px`

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

    // 关闭按钮
    document.getElementById('service-modal-close')?.addEventListener('click', () => {
      this.hideModal()
    })

    // AI解释按钮
    document.getElementById('service-ai-explain-btn')?.addEventListener('click', () => {
      this.explainWithAI()
    })

    // 点击模态框外部关闭
    this.modal?.addEventListener('click', (e) => {
      if (e.target === this.modal) {
        this.hideModal()
      }
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
   * 显示右键菜单
   */
  async showContextMenu(x: number, y: number, serviceName: string) {
    if (!this.contextMenu) return


    this.currentService = serviceName

    // 重新加载账号列表
    await this.loadAccountList()

    // 调整位置，确保菜单不会超出屏幕
    const menuWidth = 200
    const menuHeight = 600
    const adjustedX = Math.min(x, window.innerWidth - menuWidth)
    const adjustedY = Math.min(y, window.innerHeight - menuHeight)

    this.contextMenu.style.left = `${adjustedX}px`
    this.contextMenu.style.top = `${adjustedY}px`
    this.contextMenu.style.display = 'block'
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

    const titleEl = document.getElementById('service-modal-title')
    const contentEl = document.getElementById('service-modal-content')
    const explanationEl = document.getElementById('service-ai-explanation')

    if (titleEl) titleEl.textContent = title
    if (contentEl) contentEl.textContent = content

    // 隐藏AI解释区域（每次显示新内容时重置）
    if (explanationEl) {
      explanationEl.style.display = 'none'
      const explanationContentEl = document.getElementById('service-ai-explanation-content')
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

      const explanationEl = document.getElementById('service-ai-explanation')
      if (explanationEl) {
        explanationEl.style.display = 'none'
        const explanationContentEl = document.getElementById('service-ai-explanation-content')
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
    const service = this.currentService
    let command = ''
    let title = ''
    let actionName = ''

    switch (action) {
      // 基本信息
      case 'status':
        command = `systemctl status ${service} 2>/dev/null || service ${service} status 2>/dev/null || echo "无法获取服务状态"`
        title = `服务状态 - ${service}`
        actionName = '查看服务状态'
        break

      case 'config':
        command = `systemctl cat ${service} 2>/dev/null || cat /etc/init.d/${service} 2>/dev/null || echo "无法找到配置文件"`
        title = `配置文件 - ${service}`
        actionName = '查看配置文件'
        break

      case 'details':
        command = `systemctl show ${service} 2>/dev/null || echo "无法获取详细信息"`
        title = `详细信息 - ${service}`
        actionName = '查看详细信息'
        break

      case 'copy-name':
        navigator.clipboard.writeText(service)
        this.showModal('复制成功', `已复制服务名称: ${service}`)
        return

      // 服务控制
      case 'start':
        command = `systemctl start ${service} 2>&1 || service ${service} start 2>&1`
        title = `启动服务 - ${service}`
        actionName = '启动服务'
        break

      case 'stop':
        command = `systemctl stop ${service} 2>&1 || service ${service} stop 2>&1`
        title = `停止服务 - ${service}`
        actionName = '停止服务'
        break

      case 'restart':
        command = `systemctl restart ${service} 2>&1 || service ${service} restart 2>&1`
        title = `重启服务 - ${service}`
        actionName = '重启服务'
        break

      case 'reload':
        command = `systemctl reload ${service} 2>&1 || service ${service} reload 2>&1 || echo "该服务不支持reload操作"`
        title = `重新加载配置 - ${service}`
        actionName = '重新加载配置'
        break

      case 'enable':
        command = `systemctl enable ${service} 2>&1 && echo "✓ 已启用开机自启" || echo "✗ 启用失败"`
        title = `启用开机自启 - ${service}`
        actionName = '启用开机自启'
        break

      case 'disable':
        command = `systemctl disable ${service} 2>&1 && echo "✓ 已禁用开机自启" || echo "✗ 禁用失败"`
        title = `禁用开机自启 - ${service}`
        actionName = '禁用开机自启'
        break

      // 日志查询
      case 'logs':
        command = `journalctl -u ${service} -n 100 --no-pager 2>/dev/null || tail -100 /var/log/${service}.log 2>/dev/null || echo "无法获取日志"`
        title = `服务日志 - ${service}`
        actionName = '查看服务日志'
        break

      case 'errors':
        command = `journalctl -u ${service} -p err -n 50 --no-pager 2>/dev/null || grep -i error /var/log/${service}.log 2>/dev/null | tail -50 || echo "无错误日志"`
        title = `错误日志 - ${service}`
        actionName = '查看错误日志'
        break

      case 'live-logs':
        command = `echo "实时日志查看（最新20行）:"; echo ""; journalctl -u ${service} -n 20 -f --no-pager 2>/dev/null || tail -20 -f /var/log/${service}.log 2>/dev/null || echo "无法获取实时日志"`
        title = `实时日志 - ${service}`
        actionName = '查看实时日志'
        break

      // 依赖分析
      case 'dependencies':
        command = `systemctl list-dependencies ${service} --no-pager 2>/dev/null || echo "无法获取依赖信息"`
        title = `依赖服务 - ${service}`
        actionName = '查看依赖服务'
        break

      case 'reverse-dependencies':
        command = `systemctl list-dependencies ${service} --reverse --no-pager 2>/dev/null || echo "无法获取反向依赖信息"`
        title = `被依赖服务 - ${service}`
        actionName = '查看被依赖服务'
        break

      case 'service-tree':
        command = `systemctl list-dependencies ${service} --all --no-pager 2>/dev/null || echo "无法获取服务树"`
        title = `服务树 - ${service}`
        actionName = '查看服务树'
        break

      // 资源监控
      case 'cpu-usage':
        command = `echo "=== CPU使用率 ==="; echo ""; systemctl status ${service} 2>/dev/null | grep "CPU:" || ps aux | grep ${service} | grep -v grep | awk '{print "CPU: "$3"%"}' || echo "无法获取CPU使用率"`
        title = `CPU使用率 - ${service}`
        actionName = '查看CPU使用率'
        break

      case 'memory-usage':
        command = `echo "=== 内存使用 ==="; echo ""; systemctl status ${service} 2>/dev/null | grep "Memory:" || ps aux | grep ${service} | grep -v grep | awk '{print "Memory: "$4"% ("$6" KB)"}' || echo "无法获取内存使用"`
        title = `内存使用 - ${service}`
        actionName = '查看内存使用'
        break

      case 'process-list':
        command = `systemctl status ${service} 2>/dev/null | grep -A 20 "CGroup:" || ps aux | grep ${service} | grep -v grep || echo "无法获取进程列表"`
        title = `进程列表 - ${service}`
        actionName = '查看进程列表'
        break

      case 'open-files':
        command = `pid=$(systemctl show ${service} --property=MainPID --value 2>/dev/null); if [ -n "$pid" ] && [ "$pid" != "0" ]; then lsof -p $pid 2>/dev/null | head -50 || echo "无法获取打开的文件"; else echo "服务未运行或无法获取PID"; fi`
        title = `打开的文件 - ${service}`
        actionName = '查看打开的文件'
        break

      // 安全分析
      case 'run-user':
        command = `systemctl show ${service} --property=User,Group,UID,GID 2>/dev/null || ps aux | grep ${service} | grep -v grep | awk '{print "User: "$1}' || echo "无法获取运行用户"`
        title = `运行用户 - ${service}`
        actionName = '查看运行用户'
        break

      case 'permissions':
        command = `systemctl show ${service} --property=CapabilityBoundingSet,AmbientCapabilities,NoNewPrivileges,PrivateTmp,ProtectSystem,ProtectHome 2>/dev/null || echo "无法获取权限配置"`
        title = `权限配置 - ${service}`
        actionName = '查看权限配置'
        break

      case 'security-check':
        command = `echo "=== 安全配置检查 ==="; echo ""; systemctl show ${service} --property=User,DynamicUser,PrivateTmp,ProtectSystem,ProtectHome,NoNewPrivileges,PrivateDevices,ProtectKernelTunables,ProtectControlGroups,RestrictRealtime 2>/dev/null || echo "无法获取安全配置"`
        title = `安全检查 - ${service}`
        actionName = '配置安全性检查'
        break

      // 高级操作
      case 'edit-service':
        command = `systemctl cat ${service} 2>/dev/null || cat /etc/init.d/${service} 2>/dev/null || cat /lib/systemd/system/${service}.service 2>/dev/null || echo "无法找到服务文件"`
        title = `服务文件 - ${service}`
        actionName = '查看服务文件'
        break

      case 'timer':
        command = `systemctl list-timers --all | grep ${service} || echo "该服务没有关联的定时器"`
        title = `定时器配置 - ${service}`
        actionName = '查看定时器配置'
        break

      case 'environment':
        command = `systemctl show ${service} --property=Environment,EnvironmentFiles 2>/dev/null || echo "无法获取环境变量"`
        title = `环境变量 - ${service}`
        actionName = '查看环境变量'
        break

      default:
        console.warn(`未知操作: ${action}`)
        this.showModal('错误', `未知操作: ${action}`)
        return
    }

    if (!actionName) {
      actionName = '执行命令'
    }

    try {
      const accountInfo = this.selectedUsername ? ` (账号: ${this.selectedUsername})` : ''
      this.showModal(title, `⏳ 正在执行: ${actionName}${accountInfo}...\n\n命令: ${command.substring(0, 100)}${command.length > 100 ? '...' : ''}`)

      const params: any = { command }
      if (this.selectedUsername) {
        params.username = this.selectedUsername
        console.log('👤 使用账号执行服务命令:', this.selectedUsername)
      }
      const result = await invoke('ssh_execute_command_direct', params) as { output: string; exit_code: number }

      this.showModal(title, result.output || '✓ 命令执行完成，无输出')
    } catch (error) {
      this.showModal(title, `❌ 执行失败: ${error}`)
    }
  }

  /**
   * 使用AI解释当前内容
   */
  private async explainWithAI() {

    const contentEl = document.getElementById('service-modal-content')
    const explanationEl = document.getElementById('service-ai-explanation')
    const explanationContentEl = document.getElementById('service-ai-explanation-content')
    const titleEl = document.getElementById('service-modal-title')

    if (!contentEl || !explanationEl || !explanationContentEl || !titleEl) return

    const content = contentEl.textContent || ''
    const title = titleEl.textContent || ''

    explanationEl.style.display = 'block'
    explanationContentEl.textContent = '🤔 AI正在分析...'

    try {
      const settingsContent = await invoke('read_settings_file') as string
      let settings: any = {}

      if (settingsContent) {
        settings = JSON.parse(settingsContent)
      }

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

      const systemPrompt = `你是一个Linux系统管理专家，擅长分析系统服务、配置文件、日志等。请用简洁专业的语言解释用户提供的信息，重点关注服务状态、潜在问题和优化建议。

请分析并解释以下服务信息：

标题：${title}

内容：
${content}

请提供：
1. 信息概要
2. 关键发现
3. 状态评估
4. 建议操作（如果适用）`

      explanationContentEl.textContent = ''

      await this.callAIAPI(systemPrompt, providerConfig, (chunk: string) => {
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
        stream: true
      }

      console.log('📤 AI请求体:', requestBody)

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
}
