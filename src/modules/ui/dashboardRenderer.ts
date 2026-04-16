/**
 * 系统信息仪表盘渲染器
 * 负责渲染系统监控信息和统计数据
 */

import type { SystemInfo } from '../ssh/sshManager';
import { sshConnectionManager } from '../remote/sshConnectionManager';
import {
  Computer,
  TrendTwo,
  LinkOne,
  SettingTwo,
  Peoples,
  Dashboard as DashboardIcon,
  Refresh
} from '@icon-park/svg';

export class DashboardRenderer {
  private processSearchQuery = '';
  private processPageSize = 50;
  private processCurrentPage = 1;
  private history: {
    cpu: { x: number; y: number }[];
    memory: { x: number; y: number }[];
    network: { rx: { x: number; y: number }[]; tx: { x: number; y: number }[] };
    load: {
      one: { x: number; y: number }[];
      five: { x: number; y: number }[];
      fifteen: { x: number; y: number }[];
    };
  } = {
      cpu: [],
      memory: [],
      network: { rx: [], tx: [] },
      load: { one: [], five: [], fifteen: [] }
    };
  private lastNetworkData: { rx: number; tx: number; timestamp: number } | null = null;

  constructor() {
    // Expose this instance to window for dashboard refresh hooks
    (window as any).dashboardRendererInstance = this;
  }

  /**
   * 渲染系统信息仪表盘
   */
  renderDashboard(systemInfo?: SystemInfo, _theme: string = 'dark'): string {
    const isConnected = sshConnectionManager.isConnected();

    if (!isConnected) {
      return this.renderEmptyDashboard();
    }
    if (!systemInfo) {
      return this.renderConnectedButNoData();
    }

    // Update history data
    this.updateHistory(systemInfo);

    return `
      <div class="dashboard-container">
        <div class="dashboard-header">
          <div class="header-left">
            <div class="header-icon">
              ${DashboardIcon({ theme: 'filled', size: '24', fill: 'currentColor' })}
            </div>
            <div class="header-info">
              <h2>系统监控仪表盘</h2>
              <div class="last-update" id="dashboard-last-update">
                <span class="dashboard-live-dot" aria-hidden="true"></span>
                <span id="dashboard-last-update-text">最后更新: ${this.formatTime(systemInfo.lastUpdate)}</span>
                <span class="separator">•</span>
                <span>自动刷新: 3秒</span>
              </div>
            </div>
          </div>
          <button class="modern-btn secondary refresh-btn" onclick="window.loadSystemDetailedInfo(true)">
            ${Refresh({ theme: 'outline', size: '14', fill: 'currentColor' })}
            <span>刷新数据</span>
          </button>
        </div>

        <!-- 关键指标概览 (Top Row) -->
        <div class="metrics-overview">
          ${this.renderMetricCard('CPU使用率', this.getCpuUsage(systemInfo), '%', 'warning', 'dashboard-metric-cpu')}
          ${this.renderMetricCard('内存使用率', this.getMemoryUsage(systemInfo), '%', 'primary', 'dashboard-metric-memory')}
          ${this.renderMetricCard('磁盘使用率', this.getDiskUsage(systemInfo), '%', 'error', 'dashboard-metric-disk')}
          ${this.renderMetricCard('网络连接', systemInfo.networkConnections.toString(), '个', 'success', 'dashboard-metric-network')}
        </div>

        <!-- Bento Grid Layout -->
        <div class="dashboard-grid-bento">
          
          <!-- Row 1: Top Processes & Load -->
          <div class="dashboard-card modern-card top-processes-card">
             <div class="card-header">
              <div class="card-icon blue">
                ${TrendTwo({ theme: 'filled', size: '18', fill: 'currentColor' })}
              </div>
              <h3>实时 Top 进程 (CPU)</h3>
            </div>
            <div id="dashboard-top-processes" class="card-content table-container dashboard-processes-table">
              ${this.renderTopProcessesTable(systemInfo)}
            </div>
          </div>

          <div class="dashboard-card modern-card chart-load">
            <div class="card-header">
              <div class="card-icon orange">
                ${SettingTwo({ theme: 'filled', size: '18', fill: 'currentColor' })}
              </div>
              <h3>系统负载</h3>
            </div>
            <div id="dashboard-load-chart" class="card-content chart-container">
              ${this.renderLoadCardContent(systemInfo)}
            </div>
          </div>

          <!-- Row 2: Disk Space & Overview -->
          <div class="dashboard-card modern-card chart-disk" style="height: auto; min-height: 240px;">
            <div class="card-header">
              <div class="card-icon purple">
                ${Computer({ theme: 'filled', size: '18', fill: 'currentColor' })}
              </div>
              <h3>磁盘空间分布</h3>
            </div>
            <div id="dashboard-partition-list" class="card-content" style="padding: 20px; display: flex; flex-direction: column; gap: 16px;">
              ${this.renderPartitionList(systemInfo)}
            </div>
          </div>

        </div>
      </div>
    `;
  }

  public applyDashboardUpdate(systemInfo?: SystemInfo): boolean {
    if (!systemInfo) {
      return false;
    }

    this.updateHistory(systemInfo);

    const lastUpdateText = document.getElementById('dashboard-last-update-text');
    if (lastUpdateText) {
      lastUpdateText.textContent = `最后更新: ${this.formatTime(systemInfo.lastUpdate)}`;
    }

    this.updateMetricValue('dashboard-metric-cpu', this.getCpuUsage(systemInfo), '%');
    this.updateMetricValue('dashboard-metric-memory', this.getMemoryUsage(systemInfo), '%');
    this.updateMetricValue('dashboard-metric-disk', this.getDiskUsage(systemInfo), '%');
    this.updateMetricValue('dashboard-metric-network', systemInfo.networkConnections.toString(), '个');

    const partitionList = document.getElementById('dashboard-partition-list');
    if (partitionList) {
      partitionList.innerHTML = this.renderPartitionList(systemInfo);
    }

    const loadChart = document.getElementById('dashboard-load-chart');
    if (loadChart) {
      loadChart.innerHTML = this.renderLoadCardContent(systemInfo);
    }

    const topProcesses = document.getElementById('dashboard-top-processes');
    if (topProcesses) {
      topProcesses.innerHTML = this.renderTopProcessesTable(systemInfo);
    }

    const lastUpdate = document.getElementById('dashboard-last-update');
    if (lastUpdate) {
      lastUpdate.classList.remove('dashboard-data-tick');
      void lastUpdate.offsetWidth;
      lastUpdate.classList.add('dashboard-data-tick');
    }

    return true;
  }

  public setProcessSearchQuery(query: string): void {
    this.processSearchQuery = query.trim().toLowerCase();
    this.processCurrentPage = 1;
    this.refreshProcessTable();
  }

  public setProcessPageSize(pageSize: string): void {
    const nextSize = parseInt(pageSize, 10);
    this.processPageSize = Number.isFinite(nextSize) && nextSize > 0 ? nextSize : 50;
    this.processCurrentPage = 1;
    this.refreshProcessTable();
  }

  public goToProcessPage(page: number): void {
    this.processCurrentPage = Math.max(1, page);
    this.refreshProcessTable();
  }

  private refreshProcessTable(): void {
    const systemInfo = (this as any).currentSystemInfo as SystemInfo | undefined;
    const topProcesses = document.getElementById('dashboard-top-processes');
    if (systemInfo && topProcesses) {
      topProcesses.innerHTML = this.renderTopProcessesTable(systemInfo);
    }
  }

  /**
   * 渲染 Top 进程表
   */
  private renderTopProcessesTable(systemInfo: SystemInfo): string {
    if (!systemInfo.detailedInfo || !systemInfo.detailedInfo.processes || systemInfo.detailedInfo.processes.length === 0) {
      return '<div class="no-data" style="padding: 20px; text-align: center; color: var(--text-secondary);">暂无进程数据</div>';
    }

    // Sort by CPU usage (descending) and render all rows
    const processes = [...systemInfo.detailedInfo.processes]
      .sort((a, b) => parseFloat(b.cpu) - parseFloat(a.cpu));

    const filteredProcesses = this.processSearchQuery
      ? processes.filter((process) => {
        const haystack = `${process.pid} ${process.user} ${process.command}`.toLowerCase();
        return haystack.includes(this.processSearchQuery);
      })
      : processes;

    const totalProcesses = filteredProcesses.length;
    const totalPages = Math.max(1, Math.ceil(totalProcesses / this.processPageSize));
    const currentPage = Math.min(this.processCurrentPage, totalPages);
    const startIndex = (currentPage - 1) * this.processPageSize;
    const pagedProcesses = filteredProcesses.slice(startIndex, startIndex + this.processPageSize);
    this.processCurrentPage = currentPage;

    return `
      <div class="dashboard-processes-toolbar">
        <div class="dashboard-processes-toolbar-group">
          <input
            type="text"
            class="dashboard-processes-search"
            placeholder="搜索 PID / 用户 / 命令"
            value="${this.escapeHtmlAttribute(this.processSearchQuery)}"
            oninput="window.dashboardRendererInstance?.setProcessSearchQuery(this.value)"
          />
        </div>
        <div class="dashboard-processes-toolbar-group">
          <span class="dashboard-processes-toolbar-label">每页显示</span>
          <select class="dashboard-processes-page-size" onchange="window.dashboardRendererInstance?.setProcessPageSize(this.value)">
            ${[25, 50, 100, 200].map(size => `
              <option value="${size}" ${this.processPageSize === size ? 'selected' : ''}>${size}</option>
            `).join('')}
          </select>
        </div>
      </div>
      <div class="dashboard-processes-meta">
        <span>共 ${totalProcesses} 个进程</span>
        <span>第 ${currentPage} / ${totalPages} 页</span>
      </div>
      <div class="dashboard-processes-scroll">
        <table class="modern-table dashboard-processes-full-table" style="width: 100%; border-collapse: collapse; font-size: 0.9em;">
          <thead>
            <tr style="border-bottom: 1px solid var(--border-color); text-align: left;">
              <th style="padding: 8px;">PID</th>
              <th style="padding: 8px;">用户</th>
              <th style="padding: 8px;">CPU</th>
              <th style="padding: 8px;">内存</th>
              <th style="padding: 8px;">命令</th>
            </tr>
          </thead>
          <tbody>
            ${pagedProcesses.map(p => `
              <tr style="border-bottom: 1px solid var(--border-color-light);">
                <td style="padding: 8px;">${p.pid}</td>
                <td style="padding: 8px;">${p.user}</td>
                <td style="padding: 8px; color: var(--warning-color);">${p.cpu}%</td>
                <td style="padding: 8px;">${p.memory}%</td>
                <td style="padding: 8px;" title="${p.command}">${this.truncateText(p.command, 64)}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
      <div class="dashboard-processes-pagination">
        <button class="modern-btn secondary small" ${currentPage <= 1 ? 'disabled' : ''} onclick="window.dashboardRendererInstance?.goToProcessPage(${currentPage - 1})">上一页</button>
        <button class="modern-btn secondary small" ${currentPage >= totalPages ? 'disabled' : ''} onclick="window.dashboardRendererInstance?.goToProcessPage(${currentPage + 1})">下一页</button>
      </div>
    `;
  }

  private renderLoadCardContent(systemInfo: SystemInfo): string {
    return `
      ${this.renderLoadTrendChart(systemInfo)}
      <div class="load-overview-divider"></div>
      <div class="load-overview-section">
        <div class="load-overview-header">
          <div class="card-icon secondary">
            ${Peoples({ theme: 'filled', size: '16', fill: 'currentColor' })}
          </div>
          <h4>系统概览</h4>
        </div>
        <div class="info-list compact" id="dashboard-system-overview">
          ${this.renderSystemOverview(systemInfo)}
        </div>
      </div>
    `;
  }

  private renderLoadTrendChart(systemInfo: SystemInfo): string {
    const loadValues = (systemInfo.loadAverage || [])
      .map((v: string) => parseFloat(v))
      .filter((value: number) => Number.isFinite(value));

    if (loadValues.length !== 3) {
      return `
        <div class="chart-fallback-state">
          <div class="chart-fallback-title">系统负载数据不可用</div>
          <div class="chart-fallback-message">当前会话没有返回有效的 1/5/15 分钟负载值。</div>
        </div>
      `;
    }

    const loadPercentValues = loadValues.map((value) => this.normalizeLoadPercentage(value, systemInfo.cpuInfo.cores));

    const loadHistory = [
      { key: 'one', label: '1分钟负载', color: '#4f8df7', points: this.history.load.one, emphasis: true },
      { key: 'five', label: '5分钟均值', color: '#7dd3fc', points: this.history.load.five, emphasis: false },
      { key: 'fifteen', label: '15分钟均值', color: '#c4b5fd', points: this.history.load.fifteen, emphasis: false }
    ];
    const primarySeries = loadHistory[0];
    const allPoints = loadHistory.flatMap(series => series.points);
    const maxLoad = Math.max(
      1,
      ...loadPercentValues,
      ...allPoints.map(point => point.y)
    );
    const chartWidth = 560;
    const chartHeight = 240;
    const padding = { top: 16, right: 20, bottom: 34, left: 44 };
    const plotWidth = chartWidth - padding.left - padding.right;
    const plotHeight = chartHeight - padding.top - padding.bottom;
    const pointCount = Math.max(...loadHistory.map(series => series.points.length), 1);
    const yTicks = 4;

    const buildPath = (points: { x: number; y: number }[]) => {
      if (points.length === 0) {
        return '';
      }

      return points.map((point, index) => {
        const x = padding.left + (pointCount === 1 ? plotWidth / 2 : (index / (pointCount - 1)) * plotWidth);
        const y = padding.top + plotHeight - (Math.min(point.y, maxLoad) / maxLoad) * plotHeight;
        return `${index === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
      }).join(' ');
    };

    const buildAreaPath = (points: { x: number; y: number }[]) => {
      if (points.length === 0) {
        return '';
      }

      const linePath = buildPath(points);
      const startX = padding.left + (pointCount === 1 ? plotWidth / 2 : 0);
      const endX = padding.left + plotWidth;
      const baselineY = padding.top + plotHeight;
      return `${linePath} L ${endX.toFixed(1)} ${baselineY.toFixed(1)} L ${startX.toFixed(1)} ${baselineY.toFixed(1)} Z`;
    };

    const gridLines = Array.from({ length: yTicks + 1 }, (_, index) => {
      const y = padding.top + (plotHeight / yTicks) * index;
      const value = `${((maxLoad / yTicks) * (yTicks - index)).toFixed(0)}%`;
      return `
        <line x1="${padding.left}" y1="${y}" x2="${chartWidth - padding.right}" y2="${y}" class="load-chart-grid-line" />
        <text x="${padding.left - 10}" y="${y + 4}" class="load-chart-axis-label">${value}</text>
      `;
    }).join('');

    const latestLabels = this.renderLoadChartTimeLabels(pointCount, chartHeight, chartWidth, padding, plotWidth);

    return `
      <div class="load-trend-chart">
        <div class="load-chart-summary">
          ${loadHistory.map((series, index) => `
            <div class="load-summary-item">
              <span class="load-summary-dot" style="background:${series.color}"></span>
              <span class="load-summary-label">${series.label}</span>
              <span class="load-summary-value">${loadPercentValues[index].toFixed(1)}%</span>
            </div>
          `).join('')}
        </div>
        <svg viewBox="0 0 ${chartWidth} ${chartHeight}" class="load-chart-svg" preserveAspectRatio="none" aria-label="系统负载趋势图">
          ${gridLines}
          <line x1="${padding.left}" y1="${padding.top + plotHeight}" x2="${chartWidth - padding.right}" y2="${padding.top + plotHeight}" class="load-chart-axis-line" />
          <defs>
            <linearGradient id="loadPrimaryFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#4f8df7" stop-opacity="0.28" />
              <stop offset="100%" stop-color="#4f8df7" stop-opacity="0.02" />
            </linearGradient>
          </defs>
          <path d="${buildAreaPath(primarySeries.points)}" fill="url(#loadPrimaryFill)" stroke="none" />
          ${loadHistory.map(series => `
            <path
              d="${buildPath(series.points)}"
              fill="none"
              stroke="${series.color}"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
              opacity="${series.emphasis ? '1' : '0.7'}"
            />
          `).join('')}
          ${primarySeries.points.length > 0 ? (() => {
            const lastIndex = primarySeries.points.length - 1;
            const x = padding.left + (pointCount === 1 ? plotWidth / 2 : (lastIndex / (pointCount - 1)) * plotWidth);
            const y = padding.top + plotHeight - (Math.min(primarySeries.points[lastIndex].y, maxLoad) / maxLoad) * plotHeight;
            return `
              <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="5" class="load-chart-latest-point" />
              <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="10" class="load-chart-latest-ring" />
            `;
          })() : ''}
          ${latestLabels}
        </svg>
      </div>
    `;
  }

  private renderLoadChartTimeLabels(
    pointCount: number,
    chartHeight: number,
    chartWidth: number,
    padding: { top: number; right: number; bottom: number; left: number },
    plotWidth: number
  ): string {
    const labels = ['较早', '最近'];
    const positions = pointCount <= 1
      ? [padding.left + plotWidth / 2, padding.left + plotWidth / 2]
      : [padding.left, chartWidth - padding.right];

    return labels.map((label, index) => `
      <text
        x="${positions[index]}"
        y="${padding.top + (chartHeight - padding.top - padding.bottom) + 24}"
        text-anchor="${index === 0 ? 'start' : 'end'}"
        class="load-chart-axis-label"
      >${label}</text>
    `).join('');
  }

  private updateHistory(systemInfo: SystemInfo) {
    const now = new Date().getTime();

    // CPU
    const cpuUsage = parseFloat(this.getCpuUsage(systemInfo));
    this.history.cpu.push({ x: now, y: cpuUsage });
    if (this.history.cpu.length > 60) this.history.cpu.shift();

    // Memory
    const memUsage = parseFloat(this.getMemoryUsage(systemInfo));
    this.history.memory.push({ x: now, y: memUsage });
    if (this.history.memory.length > 60) this.history.memory.shift();

    // Network Speed Calculation
    let rxSpeed = 0;
    let txSpeed = 0;

    if (this.lastNetworkData && systemInfo.networkInfo) {
      const timeDiff = (now - this.lastNetworkData.timestamp) / 1000; // seconds
      if (timeDiff > 0) {
        const rxDiff = systemInfo.networkInfo.rxBytes - this.lastNetworkData.rx;
        const txDiff = systemInfo.networkInfo.txBytes - this.lastNetworkData.tx;

        // Calculate KB/s
        rxSpeed = Math.max(0, rxDiff / 1024 / timeDiff);
        txSpeed = Math.max(0, txDiff / 1024 / timeDiff);
      }
    }

    // Update last network data
    if (systemInfo.networkInfo) {
      this.lastNetworkData = {
        rx: systemInfo.networkInfo.rxBytes,
        tx: systemInfo.networkInfo.txBytes,
        timestamp: now
      };
    }

    this.history.network.rx.push({ x: now, y: rxSpeed });
    this.history.network.tx.push({ x: now, y: txSpeed });
    if (this.history.network.rx.length > 60) this.history.network.rx.shift();
    if (this.history.network.tx.length > 60) this.history.network.tx.shift();

    const loadValues = (systemInfo.loadAverage || [])
      .map((v: string) => parseFloat(v))
      .filter((value: number) => Number.isFinite(value));
    if (loadValues.length === 3) {
      this.history.load.one.push({ x: now, y: this.normalizeLoadPercentage(loadValues[0], systemInfo.cpuInfo.cores) });
      this.history.load.five.push({ x: now, y: this.normalizeLoadPercentage(loadValues[1], systemInfo.cpuInfo.cores) });
      this.history.load.fifteen.push({ x: now, y: this.normalizeLoadPercentage(loadValues[2], systemInfo.cpuInfo.cores) });

      if (this.history.load.one.length > 90) this.history.load.one.shift();
      if (this.history.load.five.length > 90) this.history.load.five.shift();
      if (this.history.load.fifteen.length > 90) this.history.load.fifteen.shift();
    }

    // Store current system info for static charts
    (this as any).currentSystemInfo = systemInfo;

    // If charts exist, update them
    // this.updateCharts();
  }

  /*
  private updateCharts() {
    if (this.charts.has('cpu-memory')) {
      this.charts.get('cpu-memory').updateSeries([{
        data: this.history.cpu
      }, {
        data: this.history.memory
      }]);
    }
    if (this.charts.has('network')) {
      this.charts.get('network').updateSeries([{
        data: this.history.network.rx
      }, {
        data: this.history.network.tx
      }]);
    }

    const systemInfo = (this as any).currentSystemInfo;
    if (systemInfo) {
      // Disk Chart - Update if exists
      if (this.charts.has('disk')) {
        const diskUsed = parseFloat(systemInfo.diskUsage.percentage.replace('%', ''));
        const diskFree = 100 - diskUsed;
        this.charts.get('disk').updateSeries([diskUsed, diskFree]);
      } else {
        // Initialize if not exists (should be handled by initCharts but just in case)
        this.initDiskChart();
      }

      // Load Chart - Update if exists
      if (this.charts.has('load')) {
        const load = systemInfo.loadAverage.map((v: string) => parseFloat(v));
        this.charts.get('load').updateSeries([{ data: load }]);
      } else {
        this.initLoadChart();
      }
    }
  }
  */

  /**
   * 渲染空仪表盘
   */
  private renderEmptyDashboard(): string {
    return `
      <div class="dashboard-empty">
        <div class="empty-state-icon">
          ${DashboardIcon({ theme: 'filled', size: '48', fill: 'currentColor' })}
        </div>
        <h3>系统监控仪表盘</h3>
        <p>请先连接到Linux服务器以查看系统监控信息。连接成功后，这里将显示详细的系统状态和性能指标。</p>
        <button class="modern-btn primary" onclick="window.showServerModal()">
          ${LinkOne({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>连接服务器</span>
        </button>
      </div>
    `;
  }

  private renderConnectedButNoData(): string {
    return `
      <div class="dashboard-empty">
        <div class="empty-state-icon">
          ${DashboardIcon({ theme: 'filled', size: '48', fill: 'currentColor' })}
        </div>
        <h3>已连接服务器，正在加载监控数据</h3>
        <p>连接状态正常，但系统监控信息尚未返回。请点击下方按钮重试加载。</p>
        <button class="modern-btn primary" onclick="window.loadSystemDetailedInfo(true)">
          ${Refresh({ theme: 'outline', size: '16', fill: 'currentColor' })}
          <span>刷新数据</span>
        </button>
      </div>
    `;
  }

  /**
   * 截断文本
   */
  private truncateText(text: string, maxLength: number): string {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - 3) + '...';
  }

  /**
   * 格式化时间
   */
  private formatTime(date: Date): string {
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }

  private normalizeLoadPercentage(load: number, cpuCores: number): number {
    const cores = Number.isFinite(cpuCores) && cpuCores > 0 ? cpuCores : 1;
    return (load / cores) * 100;
  }

  private escapeHtmlAttribute(value: string): string {
    return value
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  /**
   * 渲染指标卡片
   */
  private renderMetricCard(title: string, value: string, unit: string, type: string, id?: string): string {
    return `
      <div class="metric-card ${type}" ${id ? `id="${id}"` : ''}>
        <div class="metric-header">
          <span class="metric-title">${title}</span>
        </div>
        <div class="metric-content">
          <span class="metric-value">${value}</span>
          <span class="metric-unit">${unit}</span>
        </div>
      </div>
    `;
  }

  private updateMetricValue(id: string, value: string, unit: string): void {
    const card = document.getElementById(id);
    if (!card) {
      return;
    }

    const valueEl = card.querySelector('.metric-value');
    const unitEl = card.querySelector('.metric-unit');
    if (valueEl) {
      valueEl.textContent = value;
    }
    if (unitEl) {
      unitEl.textContent = unit;
    }
  }

  private renderSystemOverview(systemInfo: SystemInfo): string {
    return `
      <div class="info-item">
        <span class="label">主机名</span>
        <span class="value">${systemInfo.hostname}</span>
      </div>
      <div class="info-item">
        <span class="label">运行时间</span>
        <span class="value">${systemInfo.uptime}</span>
      </div>
      <div class="info-item">
        <span class="label">CPU型号</span>
        <span class="value" title="${systemInfo.cpuInfo.model}">
          ${this.truncateText(systemInfo.cpuInfo.model, 20)}
        </span>
      </div>
      <div class="info-item">
        <span class="label">核心数</span>
        <span class="value">${systemInfo.cpuInfo.cores} 核</span>
      </div>
      <div class="info-item">
        <span class="label">进程数</span>
        <span class="value">${systemInfo.processCount}</span>
      </div>
    `;
  }

  /**
   * 获取CPU使用率
   */
  private getCpuUsage(systemInfo: SystemInfo): string {
    // 从cpuInfo.usage中提取数字
    const usage = systemInfo.cpuInfo.usage.replace('%', '');
    return parseFloat(usage).toFixed(1);
  }

  /**
   * 获取内存使用率
   */
  private getMemoryUsage(systemInfo: SystemInfo): string {
    const total = this.parseMemoryValue(systemInfo.memoryUsage.total);
    const used = this.parseMemoryValue(systemInfo.memoryUsage.used);
    return ((used / total) * 100).toFixed(1);
  }

  /**
   * 获取磁盘使用率
   */
  private getDiskUsage(systemInfo: SystemInfo): string {
    return systemInfo.diskUsage.percentage.replace('%', '');
  }

  /**
   * 解析内存值
   */
  private parseMemoryValue(memStr: string): number {
    const value = parseFloat(memStr.replace(/[^\d.]/g, ''));
    if (memStr.includes('GB')) return value * 1024;
    return value;
  }

  /**
   * 渲染分区列表
   */
  private renderPartitionList(systemInfo: SystemInfo): string {
    if (!systemInfo.partitions || systemInfo.partitions.length === 0) {
      // Fallback if no partitions data (old backend or error)
      return this.renderLegacyDiskInfo(systemInfo);
    }

    return systemInfo.partitions.map(part => {
      const percentage = parseFloat(part.percentage.replace('%', ''));
      
      // Calculate color code for inline style if needed, or use CSS variables
      const colorVar = percentage > 90 ? 'var(--error-color)' : (percentage > 75 ? 'var(--warning-color)' : 'var(--primary-color)');

      return `
        <div class="partition-item" style="display: flex; flex-direction: column; gap: 6px;">
          <div class="partition-header" style="display: flex; justify-content: space-between; align-items: center; font-size: 13px;">
            <div class="partition-info" style="display: flex; align-items: center; gap: 8px;">
              <span class="partition-mount" style="font-weight: 600; color: var(--text-primary);">${part.mountpoint}</span>
              <span class="partition-fs" style="font-size: 11px; color: var(--text-secondary); background: var(--bg-tertiary); padding: 2px 6px; border-radius: 4px;">${part.filesystem}</span>
            </div>
            <div class="partition-stats" style="color: var(--text-secondary);">
              <span style="color: var(--text-primary); font-weight: 500;">${part.used}</span> / ${part.size}
            </div>
          </div>
          <div class="partition-bar-bg" style="width: 100%; height: 8px; background: var(--bg-tertiary); border-radius: 4px; overflow: hidden;">
            <div class="partition-bar-fill" style="width: ${part.percentage}; height: 100%; background: ${colorVar}; border-radius: 4px; transition: width 0.5s ease;"></div>
          </div>
          <div class="partition-footer" style="display: flex; justify-content: flex-end; font-size: 11px; color: var(--text-secondary);">
            <span>可用: <span style="color: var(--success-color);">${part.available}</span></span>
            <span style="margin: 0 4px;">•</span>
            <span>使用率: <span style="color: ${colorVar}; font-weight: 600;">${part.percentage}</span></span>
          </div>
        </div>
      `;
    }).join('');
  }

  private renderLegacyDiskInfo(systemInfo: SystemInfo): string {
    return `
      <div class="disk-detail-item" style="display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid var(--border-color); padding-bottom: 4px;">
        <span class="label" style="color: var(--text-secondary);">总空间</span>
        <span class="value" style="font-weight: 600;">${systemInfo.diskUsage.total}</span>
      </div>
      <div class="disk-detail-item" style="display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid var(--border-color); padding-bottom: 4px;">
        <span class="label" style="color: var(--text-secondary);">已使用</span>
        <span class="value" style="font-weight: 600; color: var(--error-color);">${systemInfo.diskUsage.used}</span>
      </div>
      <div class="disk-detail-item" style="display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px solid var(--border-color); padding-bottom: 4px;">
        <span class="label" style="color: var(--text-secondary);">可用空间</span>
        <span class="value" style="font-weight: 600; color: var(--success-color);">${systemInfo.diskUsage.available}</span>
      </div>
      <div class="disk-detail-item" style="display: flex; justify-content: space-between;">
        <span class="label" style="color: var(--text-secondary);">使用率</span>
        <span class="value highlight" style="font-weight: bold; color: var(--primary-color);">${systemInfo.diskUsage.percentage}</span>
      </div>
    `;
  }
}
