import { invoke } from '../../shims/@tauri-apps/api/core'
import * as IconPark from '@icon-park/svg'

/**
 * 用户列表右键菜单管理器
 */
export class UserContextMenu {
  private contextMenu: HTMLElement | null = null
  private modal: HTMLElement | null = null
  private currentUser: string = ''
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
    menu.id = 'user-context-menu'
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
        <select id="user-account-select" style="
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
          <div class="menu-item" data-action="user-details">
            <span class="menu-label">
              ${IconPark.User({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>用户详情</span>
            </span>
          </div>
          <div class="menu-item" data-action="group-info">
            <span class="menu-label">
              ${IconPark.Group({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>用户组信息</span>
            </span>
          </div>
          <div class="menu-item" data-action="home-dir">
            <span class="menu-label">
              ${IconPark.FolderOpen({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>主目录信息</span>
            </span>
          </div>
          <div class="menu-item" data-action="copy-username">
            <span class="menu-label">
              ${IconPark.Copy({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>复制用户名</span>
            </span>
          </div>
        </div>
      </div>

      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.SettingConfig({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>用户管理</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="lock-user">
            <span class="menu-label">
              ${IconPark.Lock({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>锁定用户账户</span>
            </span>
          </div>
          <div class="menu-item" data-action="unlock-user">
            <span class="menu-label">
              ${IconPark.Unlock({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>解锁用户账户</span>
            </span>
          </div>
          <div class="menu-item" data-action="delete-user">
            <span class="menu-label">
              ${IconPark.Delete({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>删除用户账户</span>
            </span>
          </div>
          <div class="menu-item" data-action="passwd-expire">
            <span class="menu-label">
              ${IconPark.Timer({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看密码过期时间</span>
            </span>
          </div>
          <div class="menu-item" data-action="user-status">
            <span class="menu-label">
              ${IconPark.CheckOne({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看账户状态</span>
            </span>
          </div>
        </div>
      </div>

      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.Lock({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>权限分析</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="sudo-permissions">
            <span class="menu-label">
              ${IconPark.Key({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看sudo权限</span>
            </span>
          </div>
          <div class="menu-item" data-action="group-membership">
            <span class="menu-label">
              ${IconPark.Group({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看用户组成员</span>
            </span>
          </div>
          <div class="menu-item" data-action="ssh-keys">
            <span class="menu-label">
              ${IconPark.Communication({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看SSH密钥</span>
            </span>
          </div>
        </div>
      </div>

      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.History({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>活动监控</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="login-history">
            <span class="menu-label">
              ${IconPark.Log({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看登录历史</span>
            </span>
          </div>
          <div class="menu-item" data-action="current-sessions">
            <span class="menu-label">
              ${IconPark.Connection({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看当前会话</span>
            </span>
          </div>
          <div class="menu-item" data-action="failed-logins">
            <span class="menu-label">
              ${IconPark.CloseOne({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看登录失败记录</span>
            </span>
          </div>
          <div class="menu-item" data-action="last-login">
            <span class="menu-label">
              ${IconPark.Time({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看最后登录时间</span>
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
          <div class="menu-item" data-action="user-processes">
            <span class="menu-label">
              ${IconPark.Application({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看用户进程</span>
            </span>
          </div>
          <div class="menu-item" data-action="disk-usage">
            <span class="menu-label">
              ${IconPark.HardDisk({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看磁盘使用</span>
            </span>
          </div>
          <div class="menu-item" data-action="open-files">
            <span class="menu-label">
              ${IconPark.FileCode({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看打开的文件</span>
            </span>
          </div>
        </div>
      </div>

      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.Protection({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>安全检查</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="abnormal-login">
            <span class="menu-label">
              ${IconPark.Attention({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>检查异常登录</span>
            </span>
          </div>
          <div class="menu-item" data-action="crontab">
            <span class="menu-label">
              ${IconPark.Schedule({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看定时任务</span>
            </span>
          </div>
          <div class="menu-item" data-action="ssh-config">
            <span class="menu-label">
              ${IconPark.Config({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看SSH配置</span>
            </span>
          </div>
          <div class="menu-item" data-action="suspicious-files">
            <span class="menu-label">
              ${IconPark.FolderFailed({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>检查可疑文件</span>
            </span>
          </div>
          <div class="menu-item" data-action="suid-files">
            <span class="menu-label">
              ${IconPark.Lightning({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看SUID文件</span>
            </span>
          </div>
        </div>
      </div>

      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.Lightning({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>快速操作</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="kill-sessions">
            <span class="menu-label">
              ${IconPark.CloseOne({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>强制退出所有会话</span>
            </span>
          </div>
          <div class="menu-item" data-action="disable-ssh">
            <span class="menu-label">
              ${IconPark.Lock({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>禁用SSH登录</span>
            </span>
          </div>
        </div>
      </div>
    `

    // 添加样式
    const style = document.createElement('style')
    style.textContent = `
      #user-context-menu .menu-item {
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
      #user-context-menu .menu-item:hover {
        background: var(--bg-tertiary);
      }
      #user-context-menu .menu-label {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      #user-context-menu .menu-label svg {
        flex-shrink: 0;
      }
      #user-context-menu .menu-parent {
        position: relative;
      }
      #user-context-menu .menu-parent .arrow {
        font-size: 10px;
        color: var(--text-secondary);
        margin-left: 8px;
      }
      #user-context-menu .submenu {
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
      #user-context-menu .menu-parent:hover > .submenu {
        display: block;
      }
      #user-context-menu .submenu .menu-item {
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
    modal.id = 'user-detail-modal'
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
          <h3 id="user-modal-title" style="margin: 0; color: var(--text-primary); font-size: 16px; flex: 1;"></h3>
          <button id="user-ai-explain-btn" class="modern-btn secondary" style="
            padding: 6px 12px;
            font-size: 13px;
            gap: 6px;
          ">
            ${IconPark.Brain({ theme: 'outline', size: '16', fill: 'currentColor' })}
            <span>AI解释</span>
          </button>
          <button id="user-modal-close" style="
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
          <div id="user-modal-content" style="
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
          <div id="user-ai-explanation" style="
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
            <div id="user-ai-explanation-content" style="
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

      const select = document.getElementById('user-account-select') as HTMLSelectElement
      if (!select) {
        console.warn('⚠️ 用户账号选择下拉框未找到')
        return
      }

      select.innerHTML = '<option value="">默认账号</option>'

      this.accounts.forEach((account: any) => {
        const option = document.createElement('option')
        option.value = account.username
        option.textContent = `${account.username}${account.description ? ` (${account.description})` : ''}${account.is_default ? ' [默认]' : ''}`
        select.appendChild(option)
      })

      //console.log(`✅ 用户右键菜单加载了 ${this.accounts.length} 个账号`)
    } catch (error) {
      console.error('❌ 用户右键菜单加载账号列表失败:', error)
    }
  }

  /**
   * 设置事件监听器
   */
  private setupEventListeners() {
    // 账号选择下拉框change事件
    document.addEventListener('change', (e) => {
      const target = e.target as HTMLElement
      if (target.id === 'user-account-select') {
        const select = target as HTMLSelectElement
        this.selectedUsername = select.value
        console.log('👤 用户菜单选择账号:', this.selectedUsername || '默认账号')
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
    document.getElementById('user-modal-close')?.addEventListener('click', () => {
      this.hideModal()
    })

    // AI解释按钮
    document.getElementById('user-ai-explain-btn')?.addEventListener('click', () => {
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
  async showContextMenu(x: number, y: number, username: string) {
    if (!this.contextMenu) return


    this.currentUser = username

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

    const titleEl = document.getElementById('user-modal-title')
    const contentEl = document.getElementById('user-modal-content')
    const explanationEl = document.getElementById('user-ai-explanation')

    if (titleEl) titleEl.textContent = title
    if (contentEl) contentEl.textContent = content

    // 隐藏AI解释区域（每次显示新内容时重置）
    if (explanationEl) {
      explanationEl.style.display = 'none'
      const explanationContentEl = document.getElementById('user-ai-explanation-content')
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

      const explanationEl = document.getElementById('user-ai-explanation')
      if (explanationEl) {
        explanationEl.style.display = 'none'
        const explanationContentEl = document.getElementById('user-ai-explanation-content')
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
    const user = this.currentUser
    let command = ''
    let title = ''
    let actionName = ''

    switch (action) {
      // 基本信息
      case 'user-details':
        command = `id ${user} 2>/dev/null && echo "" && grep "^${user}:" /etc/passwd 2>/dev/null || echo "无法获取用户详情"`
        title = `用户详情 - ${user}`
        actionName = '查看用户详情'
        break

      case 'group-info':
        command = `groups ${user} 2>/dev/null && echo "" && id ${user} 2>/dev/null || echo "无法获取用户组信息"`
        title = `用户组信息 - ${user}`
        actionName = '查看用户组信息'
        break

      case 'home-dir':
        command = `eval echo ~${user} | xargs -I {} sh -c 'echo "主目录: {}" && ls -lad {} 2>/dev/null && echo "" && du -sh {} 2>/dev/null' || echo "无法获取主目录信息"`
        title = `主目录信息 - ${user}`
        actionName = '查看主目录信息'
        break

      case 'copy-username':
        navigator.clipboard.writeText(user)
        this.showModal('复制成功', `已复制用户名: ${user}`)
        return

      // 用户管理
      case 'lock-user':
        command = `echo "锁定用户: ${user}"; echo ""; echo "命令: passwd -l ${user}"; echo "⚠️ 需要root权限执行"; echo ""; echo "执行: sudo passwd -l ${user}"`
        title = `锁定用户 - ${user}`
        actionName = '锁定用户账户'
        break

      case 'unlock-user':
        command = `echo "解锁用户: ${user}"; echo ""; echo "命令: passwd -u ${user}"; echo "⚠️ 需要root权限执行"; echo ""; echo "执行: sudo passwd -u ${user}"`
        title = `解锁用户 - ${user}`
        actionName = '解锁用户账户'
        break

      case 'delete-user':
        // Safety checks for critical users
        if (user === 'root' || user === '0') {
          this.showModal('错误', '不能删除root用户！')
          return
        }
        
        if (user === 'nobody' || user === 'daemon' || user === 'bin' || user === 'sys' || user === 'sync' || user === 'games' || user === 'man' || user === 'lp' || user === 'mail' || user === 'news' || user === 'uucp' || user === 'proxy' || user === 'www-data' || user === 'backup' || user === 'list' || user === 'irc' || user === 'gnats') {
          this.showModal('错误', `不能删除系统用户 ${user}！\n\n此用户是系统正常运行所必需的。`)
          return
        }
        
        this.showDeleteConfirmation(user)
        return

      case 'passwd-expire':
        command = `chage -l ${user} 2>/dev/null || echo "⚠️ 需要root权限查看密码过期信息"`
        title = `密码过期时间 - ${user}`
        actionName = '查看密码过期时间'
        break

      case 'user-status':
        command = `echo "=== 用户账户状态 ==="; echo ""; passwd -S ${user} 2>/dev/null || echo "⚠️ 需要root权限"; echo ""; echo "=== 最后登录 ==="; lastlog -u ${user} 2>/dev/null || echo "无登录记录"`
        title = `账户状态 - ${user}`
        actionName = '查看账户状态'
        break

      // 权限分析
      case 'sudo-permissions':
        command = `echo "=== sudo权限检查 ==="; echo ""; sudo -l -U ${user} 2>/dev/null || echo "⚠️ 需要root权限或用户无sudo权限"; echo ""; echo "=== sudoers文件检查 ==="; grep -E "^${user}|^%.*${user}" /etc/sudoers 2>/dev/null || echo "sudoers文件中未找到配置"`
        title = `sudo权限 - ${user}`
        actionName = '查看sudo权限'
        break

      case 'group-membership':
        command = `echo "=== 用户组成员 ==="; echo ""; groups ${user} 2>/dev/null; echo ""; echo "=== 详细组信息 ==="; id ${user} 2>/dev/null`
        title = `用户组成员 - ${user}`
        actionName = '查看用户组成员'
        break

      case 'ssh-keys':
        command = `home=$(eval echo ~${user}); echo "=== SSH公钥 ==="; echo ""; cat "$home/.ssh/authorized_keys" 2>/dev/null || echo "无SSH公钥"; echo ""; echo "=== SSH私钥 ==="; ls -la "$home/.ssh/" 2>/dev/null | grep -E "id_.*[^.pub]$" || echo "无SSH私钥"`
        title = `SSH密钥 - ${user}`
        actionName = '查看SSH密钥'
        break

      // 活动监控
      case 'login-history':
        command = `last ${user} -n 20 2>/dev/null || echo "无登录历史"`
        title = `登录历史 - ${user}`
        actionName = '查看登录历史'
        break

      case 'current-sessions':
        command = `who | grep "^${user} " || w ${user} 2>/dev/null || echo "用户当前未登录"`
        title = `当前会话 - ${user}`
        actionName = '查看当前会话'
        break

      case 'failed-logins':
        command = `lastb ${user} -n 20 2>/dev/null || grep "${user}" /var/log/auth.log 2>/dev/null | grep -i failed | tail -20 || echo "无失败登录记录"`
        title = `登录失败记录 - ${user}`
        actionName = '查看登录失败记录'
        break

      case 'last-login':
        command = `lastlog -u ${user} 2>/dev/null || last ${user} -n 1 2>/dev/null || echo "无登录记录"`
        title = `最后登录时间 - ${user}`
        actionName = '查看最后登录时间'
        break

      // 资源使用
      case 'user-processes':
        command = `ps -u ${user} -o pid,ppid,%cpu,%mem,vsz,rss,tty,stat,start,time,cmd 2>/dev/null || echo "用户没有运行的进程"`
        title = `用户进程 - ${user}`
        actionName = '查看用户进程'
        break

      case 'disk-usage':
        command = `home=$(eval echo ~${user}); echo "=== 主目录磁盘使用 ==="; echo ""; du -sh "$home" 2>/dev/null || echo "无法获取"; echo ""; echo "=== 详细统计 ==="; du -h --max-depth=1 "$home" 2>/dev/null | sort -hr | head -20 || echo "无法获取详细统计"`
        title = `磁盘使用 - ${user}`
        actionName = '查看磁盘使用'
        break

      case 'open-files':
        command = `lsof -u ${user} 2>/dev/null | head -100 || echo "⚠️ 需要root权限或用户无打开的文件"`
        title = `打开的文件 - ${user}`
        actionName = '查看打开的文件'
        break

      // 安全检查
      case 'abnormal-login':
        command = `echo "=== 异常登录检查 ==="; echo ""; echo "1. 非工作时间登录:"; last ${user} 2>/dev/null | awk '{if($7 ~ /[0-2][0-9]:[0-5][0-9]/ || $7 ~ /0[0-6]:[0-5][0-9]/) print}' | head -10 || echo "无记录"; echo ""; echo "2. 异地登录:"; last ${user} -i 2>/dev/null | head -20 || echo "无记录"`
        title = `异常登录检查 - ${user}`
        actionName = '检查异常登录'
        break

      case 'crontab':
        command = `echo "=== 用户定时任务 ==="; echo ""; crontab -u ${user} -l 2>/dev/null || echo "无定时任务或需要权限"; echo ""; echo "=== 系统定时任务 ==="; grep -r "${user}" /etc/cron* 2>/dev/null | head -20 || echo "无相关系统定时任务"`
        title = `定时任务 - ${user}`
        actionName = '查看定时任务'
        break

      case 'ssh-config':
        command = `home=$(eval echo ~${user}); echo "=== SSH客户端配置 ==="; echo ""; cat "$home/.ssh/config" 2>/dev/null || echo "无SSH配置文件"; echo ""; echo "=== known_hosts ==="; wc -l "$home/.ssh/known_hosts" 2>/dev/null || echo "无known_hosts文件"`
        title = `SSH配置 - ${user}`
        actionName = '查看SSH配置'
        break

      case 'suspicious-files':
        command = `home=$(eval echo ~${user}); echo "=== 可疑文件检查 ==="; echo ""; echo "1. 隐藏文件:"; find "$home" -name ".*" -type f 2>/dev/null | head -20; echo ""; echo "2. 最近修改的文件:"; find "$home" -type f -mtime -7 2>/dev/null | head -20`
        title = `可疑文件检查 - ${user}`
        actionName = '检查可疑文件'
        break

      case 'suid-files':
        command = `home=$(eval echo ~${user}); echo "=== SUID文件检查 ==="; echo ""; find "$home" -perm -4000 -type f 2>/dev/null | head -20 || echo "未找到SUID文件"; echo ""; echo "=== SGID文件检查 ==="; find "$home" -perm -2000 -type f 2>/dev/null | head -20 || echo "未找到SGID文件"`
        title = `SUID文件 - ${user}`
        actionName = '查看SUID文件'
        break

      // 快速操作
      case 'kill-sessions':
        command = `echo "强制退出用户会话: ${user}"; echo ""; echo "命令: pkill -u ${user} 或 killall -u ${user}"; echo "⚠️ 需要root权限执行"; echo ""; ps -u ${user} -o pid,cmd 2>/dev/null || echo "用户没有运行的进程"`
        title = `强制退出会话 - ${user}`
        actionName = '强制退出所有会话'
        break

      case 'disable-ssh':
        command = `echo "禁用SSH登录: ${user}"; echo ""; echo "方法1: 编辑 /etc/ssh/sshd_config"; echo "添加: DenyUsers ${user}"; echo ""; echo "方法2: 使用PAM"; echo "编辑 /etc/security/access.conf"; echo "添加: -:${user}:ALL"; echo ""; echo "⚠️ 需要root权限执行并重启SSH服务"`
        title = `禁用SSH登录 - ${user}`
        actionName = '禁用SSH登录'
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
        console.log('👤 使用账号执行用户命令:', this.selectedUsername)
      }
      const result = await invoke('ssh_execute_command_direct', params) as { output: string; exit_code: number }

      this.showModal(title, result.output || '✓ 命令执行完成，无输出')
    } catch (error) {
      this.showModal(title, `❌ 执行失败: ${error}`)
    }
  }

  /**
   * 显示删除用户确认对话框
   */
  private showDeleteConfirmation(username: string) {
    // 创建确认对话框
    const confirmModal = document.createElement('div')
    confirmModal.id = 'delete-user-confirm-modal'
    confirmModal.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.6);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10002;
    `

    confirmModal.innerHTML = `
      <div class="modal-content" style="
        background: var(--bg-primary);
        border-radius: var(--border-radius);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        max-width: 500px;
        width: 90%;
        padding: 0;
      ">
        <div class="modal-header" style="
          padding: var(--spacing-md);
          border-bottom: 1px solid var(--border-color);
          display: flex;
          align-items: center;
          gap: var(--spacing-md);
        ">
          ${IconPark.Delete({ theme: 'filled', size: '24', fill: '#ef4444' })}
          <h3 style="margin: 0; color: #ef4444; font-size: 18px;">删除用户确认</h3>
        </div>
        <div class="modal-body" style="
          padding: var(--spacing-md);
          color: var(--text-primary);
        ">
          <div style="margin-bottom: var(--spacing-md);">
            <strong style="color: #ef4444;">⚠️ 危险操作：即将删除用户 <code style="background: var(--bg-secondary); padding: 2px 6px; border-radius: 4px;">${username}</code></strong>
          </div>
          
          <div style="margin-bottom: var(--spacing-md);">
            <strong>此操作将永久删除：</strong>
            <ul style="margin: 8px 0; padding-left: 20px;">
              <li>用户账户 <code>${username}</code></li>
              <li>用户主目录 <code>/home/${username}</code></li>
              <li>用户邮件池</li>
              <li>用户所属的组（如果组中没有其他用户）</li>
            </ul>
          </div>
          
          <div style="margin-bottom: var(--spacing-md); padding: var(--spacing-sm); background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: var(--border-radius-sm);">
            <strong style="color: #ef4444;">⚠️ 此操作不可撤销！</strong>
          </div>
          
          <div style="margin-bottom: var(--spacing-md);">
            <strong>执行前请确认：</strong>
            <ul style="margin: 8px 0; padding-left: 20px; font-size: 13px;">
              <li>✓ 用户没有重要数据需要备份</li>
              <li>✓ 用户没有正在运行的进程</li>
              <li>✓ 已备份所有重要文件</li>
              <li>✓ 确认此用户不再需要</li>
            </ul>
          </div>
          
          <div style="padding: var(--spacing-sm); background: var(--bg-secondary); border-radius: var(--border-radius-sm); font-family: var(--font-mono); font-size: 12px;">
            <strong>执行命令：</strong><br>
            sudo userdel -r ${username}
          </div>
        </div>
        <div class="modal-footer" style="
          padding: var(--spacing-md);
          border-top: 1px solid var(--border-color);
          display: flex;
          justify-content: flex-end;
          gap: var(--spacing-sm);
        ">
          <button id="delete-user-cancel" class="modern-btn secondary" style="
            padding: 8px 16px;
            font-size: 14px;
          ">取消</button>
          <button id="delete-user-confirm" class="modern-btn danger" style="
            padding: 8px 16px;
            font-size: 14px;
            background: #ef4444;
            border-color: #ef4444;
          ">确认删除</button>
        </div>
      </div>
    `

    document.body.appendChild(confirmModal)

    // 绑定事件
    document.getElementById('delete-user-cancel')?.addEventListener('click', () => {
      document.body.removeChild(confirmModal)
    })

    document.getElementById('delete-user-confirm')?.addEventListener('click', async () => {
      document.body.removeChild(confirmModal)
      await this.executeDeleteUser(username)
    })

    // 点击外部关闭
    confirmModal.addEventListener('click', (e) => {
      if (e.target === confirmModal) {
        document.body.removeChild(confirmModal)
      }
    })

    // ESC键关闭
    const escHandler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        document.body.removeChild(confirmModal)
        document.removeEventListener('keydown', escHandler)
      }
    }
    document.addEventListener('keydown', escHandler)
  }

  /**
   * 执行删除用户操作
   */
  private async executeDeleteUser(username: string) {
    const command = `sudo userdel -r ${username}`
    const title = `删除用户 - ${username}`

    try {
      const accountInfo = this.selectedUsername ? ` (账号: ${this.selectedUsername})` : ''
      this.showModal(title, `⏳ 正在删除用户: ${username}${accountInfo}...`)

      const params: any = { command }
      if (this.selectedUsername) {
        params.username = this.selectedUsername
        console.log('👤 使用账号执行删除用户命令:', this.selectedUsername)
      }
      
      const result = await invoke('ssh_execute_command_direct', params) as { output: string; exit_code: number }

      if (result.exit_code === 0) {
        this.showModal(title, `✓ 用户 ${username} 删除成功！\n\n${result.output || ''}`)
      } else {
        this.showModal(title, `❌ 删除用户失败：\n\n${result.output || '未知错误'}`)
      }
    } catch (error) {
      this.showModal(title, `❌ 删除用户失败: ${error}`)
    }
  }

  /**
   * 使用AI解释当前内容
   */
  private async explainWithAI() {
    const contentEl = document.getElementById('user-modal-content')
    const explanationEl = document.getElementById('user-ai-explanation')
    const explanationContentEl = document.getElementById('user-ai-explanation-content')
    const titleEl = document.getElementById('user-modal-title')

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

      const systemPrompt = `你是一个Linux用户管理专家，擅长分析用户权限、登录历史、安全配置等。请用简洁专业的语言解释用户提供的信息，重点关注安全风险和权限问题。

请分析并解释以下用户信息：

标题：${title}

内容：
${content}

请提供：
1. 信息概要
2. 关键发现
3. 安全评估（如果适用）
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
