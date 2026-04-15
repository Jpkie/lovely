import { invoke } from '../../shims/@tauri-apps/api/core'
import * as IconPark from '@icon-park/svg'

/**
 * 计划任务右键菜单管理器
 */
export class CronContextMenu {
  private contextMenu: HTMLElement | null = null
  private modal: HTMLElement | null = null
  private currentCron: {
    user: string
    schedule: string
    command: string
    source: string
  } | null = null
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
    menu.id = 'cron-context-menu'
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
        <select id="cron-account-select" style="
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
          ${IconPark.FileCode({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>源文件操作</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="view-source">
            <span class="menu-label">
              ${IconPark.Find({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看源文件内容</span>
            </span>
          </div>
          <div class="menu-item" data-action="delete-task-file">
            <span class="menu-label">
              ${IconPark.Delete({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>删除任务及文件</span>
            </span>
          </div>
        </div>
      </div>

      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.Info({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>基本信息</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="details">
            <span class="menu-label">
              ${IconPark.FileText({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看任务详情</span>
            </span>
          </div>
          <div class="menu-item" data-action="schedule">
            <span class="menu-label">
              ${IconPark.Schedule({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看执行时间表</span>
            </span>
          </div>
          <div class="menu-item" data-action="command">
            <span class="menu-label">
              ${IconPark.Terminal({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看执行命令</span>
            </span>
          </div>
          <div class="menu-item" data-action="copy-command">
            <span class="menu-label">
              ${IconPark.Copy({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>复制命令</span>
            </span>
          </div>
        </div>
      </div>

      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.SettingConfig({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>任务管理</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="run-now">
            <span class="menu-label">
              ${IconPark.Play({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>立即执行</span>
            </span>
          </div>
          <div class="menu-item" data-action="test-command">
            <span class="menu-label">
              ${IconPark.Experiment({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>测试命令</span>
            </span>
          </div>
          <div class="menu-item" data-action="view-crontab">
            <span class="menu-label">
              ${IconPark.FileSearch({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看完整crontab</span>
            </span>
          </div>
        </div>
      </div>

      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.Log({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>执行历史</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="execution-logs">
            <span class="menu-label">
              ${IconPark.FileText({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看执行日志</span>
            </span>
          </div>
          <div class="menu-item" data-action="recent-runs">
            <span class="menu-label">
              ${IconPark.History({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>最近执行记录</span>
            </span>
          </div>
          <div class="menu-item" data-action="error-logs">
            <span class="menu-label">
              ${IconPark.Caution({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>查看错误日志</span>
            </span>
          </div>
        </div>
      </div>

      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.Time({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>时间分析</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="parse-cron">
            <span class="menu-label">
              ${IconPark.Analysis({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>解析cron表达式</span>
            </span>
          </div>
          <div class="menu-item" data-action="next-run">
            <span class="menu-label">
              ${IconPark.Timer({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>下次执行时间</span>
            </span>
          </div>
          <div class="menu-item" data-action="frequency">
            <span class="menu-label">
              ${IconPark.ChartLine({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>执行频率分析</span>
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
          <div class="menu-item" data-action="security-check">
            <span class="menu-label">
              ${IconPark.Shield({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>命令安全性检查</span>
            </span>
          </div>
          <div class="menu-item" data-action="check-path">
            <span class="menu-label">
              ${IconPark.FolderOpen({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>检查命令路径</span>
            </span>
          </div>
          <div class="menu-item" data-action="suspicious-check">
            <span class="menu-label">
              ${IconPark.Attention({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>可疑命令检测</span>
            </span>
          </div>
        </div>
      </div>

      <div class="menu-item menu-parent">
        <span class="menu-label">
          ${IconPark.SettingTwo({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>高级操作</span>
        </span>
        <span class="arrow">▶</span>
        <div class="submenu">
          <div class="menu-item" data-action="backup">
            <span class="menu-label">
              ${IconPark.Save({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>备份crontab</span>
            </span>
          </div>
          <div class="menu-item" data-action="export">
            <span class="menu-label">
              ${IconPark.Export({ theme: 'outline', size: '14', fill: 'currentColor' })}
              <span>导出任务配置</span>
            </span>
          </div>
        </div>
      </div>
    `

    // 添加样式
    const style = document.createElement('style')
    style.textContent = `
      #cron-context-menu .menu-item {
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
      #cron-context-menu .menu-item:hover {
        background: var(--bg-tertiary);
      }
      #cron-context-menu .menu-label {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      #cron-context-menu .menu-label svg {
        flex-shrink: 0;
      }
      #cron-context-menu .menu-parent {
        position: relative;
      }
      #cron-context-menu .menu-parent .arrow {
        font-size: 10px;
        color: var(--text-secondary);
        margin-left: 8px;
      }
      #cron-context-menu .submenu {
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
      #cron-context-menu .menu-parent:hover > .submenu {
        display: block;
      }
      #cron-context-menu .submenu .menu-item {
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
    modal.id = 'cron-detail-modal'
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
          <h3 id="cron-modal-title" style="margin: 0; color: var(--text-primary); font-size: 16px; flex: 1;"></h3>
          <button id="cron-ai-explain-btn" class="modern-btn secondary" style="
            padding: 6px 12px;
            font-size: 13px;
            gap: 6px;
          ">
            ${IconPark.Brain({ theme: 'outline', size: '16', fill: 'currentColor' })}
            <span>AI解释</span>
          </button>
          <button id="cron-modal-close" style="
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
          <div id="cron-modal-content" style="
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
          <div id="cron-ai-explanation" style="
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
            <div id="cron-ai-explanation-content" style="
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

      const select = document.getElementById('cron-account-select') as HTMLSelectElement
      if (!select) {
        console.warn('⚠️ 计划任务账号选择下拉框未找到')
        return
      }

      select.innerHTML = '<option value="">默认账号</option>'

      this.accounts.forEach((account: any) => {
        const option = document.createElement('option')
        option.value = account.username
        option.textContent = `${account.username}${account.description ? ` (${account.description})` : ''}${account.is_default ? ' [默认]' : ''}`
        select.appendChild(option)
      })

      //console.log(`✅ 计划任务右键菜单加载了 ${this.accounts.length} 个账号`)
    } catch (error) {
      console.error('❌ 计划任务右键菜单加载账号列表失败:', error)
    }
  }

  /**
   * 设置事件监听器
   */
  private setupEventListeners() {
    // 账号选择下拉框change事件
    document.addEventListener('change', (e) => {
      const target = e.target as HTMLElement
      if (target.id === 'cron-account-select') {
        const select = target as HTMLSelectElement
        this.selectedUsername = select.value
        console.log('👤 计划任务菜单选择账号:', this.selectedUsername || '默认账号')
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
    document.getElementById('cron-modal-close')?.addEventListener('click', () => {
      this.hideModal()
    })

    // AI解释按钮
    document.getElementById('cron-ai-explain-btn')?.addEventListener('click', () => {
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
  async showContextMenu(x: number, y: number, cron: {
    user: string
    schedule: string
    command: string
    source: string
  }) {
    if (!this.contextMenu) return


    this.currentCron = cron

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

    const titleEl = document.getElementById('cron-modal-title')
    const contentEl = document.getElementById('cron-modal-content')
    const explanationEl = document.getElementById('cron-ai-explanation')

    if (titleEl) titleEl.textContent = title
    if (contentEl) contentEl.textContent = content

    // 隐藏AI解释区域（每次显示新内容时重置）
    if (explanationEl) {
      explanationEl.style.display = 'none'
      const explanationContentEl = document.getElementById('cron-ai-explanation-content')
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

      const explanationEl = document.getElementById('cron-ai-explanation')
      if (explanationEl) {
        explanationEl.style.display = 'none'
        const explanationContentEl = document.getElementById('cron-ai-explanation-content')
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
    if (!this.currentCron) return

    const { user, schedule, command, source } = this.currentCron
    let cmd = ''
    let title = ''
    let actionName = ''

    switch (action) {
      // 源文件操作
      case 'view-source':
        if (source && source.startsWith('/')) {
            cmd = `echo "=== 源文件: ${source} ==="; echo ""; cat "${source}" 2>&1 || echo "无法读取文件"`
            title = `源文件 - ${source}`
        } else if (source && source.startsWith('crontab:')) {
             const u = source.split(':')[1];
             cmd = `echo "=== 用户Crontab: ${u} ==="; echo ""; crontab -u ${u} -l`
             title = `用户Crontab - ${u}`
        } else {
             this.showModal('提示', '无法确定源文件位置');
             return;
        }
        actionName = '查看源文件'
        break

      case 'delete-task-file':
         if (source && source.startsWith('/')) {
             // Safety check: Don't delete /etc/crontab
             if (source === '/etc/crontab') {
                 this.showModal('错误', '不能删除系统主crontab文件 (/etc/crontab)');
                 return;
             }
             
             cmd = `echo "正在删除文件: ${source}"; rm -f "${source}" && echo "✓ 删除成功" || echo "✗ 删除失败"`
             title = `删除任务文件 - ${source}`
             actionName = '删除任务文件'
         } else {
             this.showModal('提示', '此任务不是通过独立文件配置的，无法通过删除文件来删除任务。\n\n如果是用户任务，请使用"crontab -e"编辑。');
             return;
         }
         break

      // 基本信息
      case 'details':
        cmd = `echo "=== 计划任务详情 ==="; echo ""; echo "用户: ${user}"; echo "时间表: ${schedule}"; echo "命令: ${command}"; echo ""; echo "=== 任务状态 ==="; crontab -u ${user} -l 2>/dev/null | grep -F "${command}" || echo "任务可能已被删除或修改"`
        title = `计划任务详情 - ${user}`
        actionName = '查看任务详情'
        break

      case 'schedule':
        cmd = `echo "=== 执行时间表分析 ==="; echo ""; echo "Cron表达式: ${schedule}"; echo ""; echo "字段说明:"; echo "分钟(0-59) 小时(0-23) 日(1-31) 月(1-12) 星期(0-7)"; echo ""; echo "当前表达式解析:"; echo "${schedule}" | awk '{print "分钟: "$1; print "小时: "$2; print "日期: "$3; print "月份: "$4; print "星期: "$5}'`
        title = `执行时间表 - ${schedule}`
        actionName = '查看执行时间表'
        break

      case 'command':
        cmd = `echo "=== 执行命令 ==="; echo ""; echo "${command}"; echo ""; echo "=== 命令分析 ==="; which ${command.split(' ')[0]} 2>/dev/null || echo "命令路径: 未找到或不在PATH中"`
        title = `执行命令 - ${command.substring(0, 50)}...`
        actionName = '查看执行命令'
        break

      case 'copy-command':
        navigator.clipboard.writeText(command)
        this.showModal('复制成功', `已复制命令: ${command}`)
        return

      // 任务管理
      case 'run-now':
        cmd = `echo "立即执行计划任务"; echo ""; echo "用户: ${user}"; echo "命令: ${command}"; echo ""; echo "执行中..."; echo ""; ${command}`
        title = `立即执行 - ${command.substring(0, 50)}...`
        actionName = '立即执行任务'
        break

      case 'test-command':
        cmd = `echo "=== 测试命令 ==="; echo ""; echo "命令: ${command}"; echo ""; echo "检查命令语法..."; bash -n -c "${command}" 2>&1 && echo "✓ 语法检查通过" || echo "✗ 语法错误"; echo ""; echo "⚠️ 提示：这只是语法检查，实际执行可能需要其他条件"`
        title = `测试命令 - ${command.substring(0, 50)}...`
        actionName = '测试命令'
        break

      case 'view-crontab':
        cmd = `crontab -u ${user} -l 2>/dev/null || echo "用户 ${user} 没有crontab"`
        title = `完整crontab - ${user}`
        actionName = '查看完整crontab'
        break

      // 执行历史
      case 'execution-logs':
        cmd = `echo "=== 计划任务执行日志 ==="; echo ""; echo "搜索关键词: ${command.split(' ')[0]}"; echo ""; grep CRON /var/log/syslog 2>/dev/null | grep "${user}" | grep "${command.split(' ')[0]}" | tail -50 || journalctl -u cron 2>/dev/null | grep "${user}" | grep "${command.split(' ')[0]}" | tail -50 || echo "无执行日志或日志文件不可访问"`
        title = `执行日志 - ${command.substring(0, 50)}...`
        actionName = '查看执行日志'
        break

      case 'recent-runs':
        cmd = `echo "=== 最近执行记录 ==="; echo ""; grep CRON /var/log/syslog 2>/dev/null | grep "(${user})" | tail -20 || journalctl -u cron 2>/dev/null | grep "${user}" | tail -20 || echo "无执行记录"`
        title = `最近执行记录 - ${user}`
        actionName = '查看最近执行记录'
        break

      case 'error-logs':
        cmd = `echo "=== 错误日志 ==="; echo ""; grep -i "error\\|fail\\|cron" /var/log/syslog 2>/dev/null | grep "${user}" | tail -30 || journalctl -p err 2>/dev/null | grep cron | grep "${user}" | tail -30 || echo "无错误日志"`
        title = `错误日志 - ${user}`
        actionName = '查看错误日志'
        break

      // 时间分析
      case 'parse-cron':
        cmd = `echo "=== Cron表达式解析 ==="; echo ""; echo "表达式: ${schedule}"; echo ""; if [[ "${schedule}" == "@hourly" ]]; then echo "含义: 每小时执行一次 (0 * * * *)"; elif [[ "${schedule}" == "@daily" ]] || [[ "${schedule}" == "@midnight" ]]; then echo "含义: 每天午夜执行 (0 0 * * *)"; elif [[ "${schedule}" == "@weekly" ]]; then echo "含义: 每周日午夜执行 (0 0 * * 0)"; elif [[ "${schedule}" == "@monthly" ]]; then echo "含义: 每月1号午夜执行 (0 0 1 * *)"; elif [[ "${schedule}" == "@yearly" ]] || [[ "${schedule}" == "@annually" ]]; then echo "含义: 每年1月1日午夜执行 (0 0 1 1 *)"; elif [[ "${schedule}" == "@reboot" ]]; then echo "含义: 系统启动时执行"; else echo "标准cron表达式"; echo "${schedule}" | awk '{print "分钟: "$1" (0-59)"; print "小时: "$2" (0-23)"; print "日期: "$3" (1-31)"; print "月份: "$4" (1-12)"; print "星期: "$5" (0-7, 0和7都表示周日)"}'; fi`
        title = `Cron表达式解析 - ${schedule}`
        actionName = '解析cron表达式'
        break

      case 'next-run':
        cmd = `echo "=== 下次执行时间 ==="; echo ""; echo "当前时间: $(date '+%Y-%m-%d %H:%M:%S')"; echo "时间表: ${schedule}"; echo ""; echo "⚠️ 注意：精确计算需要安装croniter等工具"; echo ""; if [[ "${schedule}" == "@hourly" ]]; then echo "下次执行: 下一个整点"; elif [[ "${schedule}" == "@daily" ]]; then echo "下次执行: 明天 00:00"; elif [[ "${schedule}" == "@weekly" ]]; then echo "下次执行: 下周日 00:00"; elif [[ "${schedule}" == "@monthly" ]]; then echo "下次执行: 下月1日 00:00"; else echo "标准cron表达式，请使用cron计算工具"; fi`
        title = `下次执行时间 - ${schedule}`
        actionName = '查看下次执行时间'
        break

      case 'frequency':
        cmd = `echo "=== 执行频率分析 ==="; echo ""; echo "时间表: ${schedule}"; echo ""; if [[ "${schedule}" == "@hourly" ]]; then echo "频率: 每小时1次"; echo "每天: 24次"; echo "每月: ~720次"; elif [[ "${schedule}" == "@daily" ]]; then echo "频率: 每天1次"; echo "每月: ~30次"; echo "每年: 365次"; elif [[ "${schedule}" == "@weekly" ]]; then echo "频率: 每周1次"; echo "每月: ~4次"; echo "每年: 52次"; elif [[ "${schedule}" == "@monthly" ]]; then echo "频率: 每月1次"; echo "每年: 12次"; elif [[ "${schedule}" =~ ^\\*.*\\*.*\\*.*\\*.*\\*$ ]]; then echo "频率: 每分钟1次"; echo "每小时: 60次"; echo "每天: 1440次"; else echo "自定义频率"; echo "请根据cron表达式计算"; fi`
        title = `执行频率 - ${schedule}`
        actionName = '执行频率分析'
        break

      // 安全检查
      case 'security-check':
        cmd = `echo "=== 命令安全性检查 ==="; echo ""; echo "命令: ${command}"; echo ""; echo "1. 检查危险命令:"; if echo "${command}" | grep -qE "rm -rf|dd if=|mkfs|fdisk|>/dev/"; then echo "⚠️ 包含危险命令"; else echo "✓ 未发现明显危险命令"; fi; echo ""; echo "2. 检查网络操作:"; if echo "${command}" | grep -qE "wget|curl|nc|telnet|ssh"; then echo "⚠️ 包含网络操作命令"; else echo "✓ 未检测到网络操作"; fi; echo ""; echo "3. 检查权限提升:"; if echo "${command}" | grep -qE "sudo|su -"; then echo "⚠️ 包含权限提升命令"; else echo "✓ 未检测到权限提升"; fi`
        title = `安全检查 - ${command.substring(0, 50)}...`
        actionName = '命令安全性检查'
        break

      case 'check-path':
        cmd = `echo "=== 命令路径检查 ==="; echo ""; cmd_name="${command.split(' ')[0]}"; echo "命令: $cmd_name"; echo ""; which "$cmd_name" 2>/dev/null && echo "" && ls -la $(which "$cmd_name") 2>/dev/null || echo "⚠️ 命令不在PATH中或不存在"`
        title = `路径检查 - ${command.split(' ')[0]}`
        actionName = '检查命令路径'
        break

      case 'suspicious-check':
        cmd = `echo "=== 可疑命令检测 ==="; echo ""; echo "命令: ${command}"; echo ""; echo "检测项:"; echo ""; echo "1. 编码/混淆:"; if echo "${command}" | grep -qE "base64|eval|exec"; then echo "⚠️ 可能包含编码或混淆"; else echo "✓ 未发现编码"; fi; echo ""; echo "2. 反弹shell:"; if echo "${command}" | grep -qE "bash -i|/bin/sh|nc.*-e"; then echo "⚠️ 可能是反弹shell"; else echo "✓ 未发现反弹shell特征"; fi; echo ""; echo "3. 下载执行:"; if echo "${command}" | grep -qE "curl.*\\||wget.*\\||chmod\\+x"; then echo "⚠️ 可能下载并执行文件"; else echo "✓ 未发现下载执行"; fi`
        title = `可疑检测 - ${command.substring(0, 50)}...`
        actionName = '可疑命令检测'
        break

      // 高级操作
      case 'backup':
        cmd = `echo "=== 备份crontab ==="; echo ""; backup_file="/tmp/crontab_${user}_$(date +%Y%m%d_%H%M%S).bak"; crontab -u ${user} -l > "$backup_file" 2>/dev/null && echo "✓ 备份成功" && echo "备份文件: $backup_file" && echo "" && cat "$backup_file" || echo "✗ 备份失败"`
        title = `备份crontab - ${user}`
        actionName = '备份crontab'
        break

      case 'export':
        cmd = `echo "=== 导出任务配置 ==="; echo ""; echo "用户: ${user}"; echo "时间表: ${schedule}"; echo "命令: ${command}"; echo ""; echo "JSON格式:"; echo "{"; echo '  "user": "'${user}'",'; echo '  "schedule": "'${schedule}'",'; echo '  "command": "'${command}'"'; echo "}"`
        title = `导出配置 - ${command.substring(0, 50)}...`
        actionName = '导出任务配置'
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
      this.showModal(title, `⏳ 正在执行: ${actionName}${accountInfo}...\n\n命令: ${cmd.substring(0, 100)}${cmd.length > 100 ? '...' : ''}`)

      const params: any = { command: cmd }
      if (this.selectedUsername) {
        params.username = this.selectedUsername
        console.log('👤 使用账号执行计划任务命令:', this.selectedUsername)
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

    const contentEl = document.getElementById('cron-modal-content')
    const explanationEl = document.getElementById('cron-ai-explanation')
    const explanationContentEl = document.getElementById('cron-ai-explanation-content')
    const titleEl = document.getElementById('cron-modal-title')

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

      const systemPrompt = `你是一个Linux系统管理和cron专家，擅长分析计划任务、cron表达式、命令安全性等。请用简洁专业的语言解释用户提供的信息，重点关注任务的作用、执行时间和潜在风险。

请分析并解释以下计划任务信息：

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
