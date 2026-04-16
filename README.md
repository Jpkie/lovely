# LovelyRes

LovelyRes 是一个面向 Linux 应急响应与远程运维场景的桌面化工具集。当前仓库实际采用：

- 前端：`Vue 3 + TypeScript + Vite`
- 后端：`Python FastAPI`
- 终端：`xterm.js`
- 前后端通信：通过 Tauri 风格 `invoke` 兼容层映射到 Python HTTP API

这份 README 基于当前仓库代码结构编写，不沿用历史上的 Rust/Tauri 主实现描述。

## 当前状态

当前主应用代码位于仓库根目录：

- 前端业务代码：`src/`
- Python 后端：`src-python/`
- 前端入口页面：`index.html`、`ssh-terminal.html`、`container-terminal.html`

仓库中另有一个独立的 `lovely/` 子目录，它是一个单独的 Vite 示例项目，不是当前主业务前端入口。

## 功能概览

当前前端已经实现或部分实现的主要能力：

- SSH 连接管理
- 多标签 SSH 终端
- SFTP 文件浏览与基础文件操作
- 系统信息与仪表盘展示
- 快速检测与安全排查
- 日志审计
- AI 辅助分析与终端命令建议
- 设置管理与主题/字体切换
- Payload 工具页面嵌入

## 架构说明

### 1. 前端不是标准单一 Vue SPA

这个项目采用混合式前端架构：

- 页面骨架和大部分业务界面由字符串模板渲染
- 少数复杂区域使用 Vue 组件
- 交互大量通过全局 `window` 函数桥接
- 页面切换主要依赖内部状态和重新渲染，而不是 Vue Router

最典型的例子：

- 主应用骨架由 `src/modules/core/app.ts` 和 `src/modules/ui/modernUIRenderer.ts` 渲染
- SSH 终端由 `src/components/SSHTerminal.vue` 提供

### 2. 前后端调用方式

代码中大量保留了 `invoke('xxx')` 调用形式，但当前并不直接依赖 Rust 命令实现，而是通过兼容层转发到 Python 后端：

- Tauri shim：`src/shims/@tauri-apps/api/core.ts`
- Python API 适配层：`src/config/python-api.config.ts`

开发时前端通常通过 Vite 代理访问后端：

- 前端：`http://127.0.0.1:1420`
- 后端：`http://127.0.0.1:3001`

## 目录结构

```text
.
├─ src/                        # 主前端源码
│  ├─ components/             # Vue 组件，核心是 SSHTerminal.vue
│  ├─ config/                 # API 与 invoke 适配配置
│  ├─ css/                    # 全局样式与主题
│  ├─ modules/                # 业务模块
│  │  ├─ core/                # 应用入口、状态管理
│  │  ├─ ui/                  # 字符串模板渲染器、弹窗、右键菜单
│  │  ├─ remote/              # SSH 当前连接、SFTP、远程操作协调
│  │  ├─ ssh/                 # SSH 配置、终端管理、命令提示
│  │  ├─ system/              # 系统信息采集与解析
│  │  ├─ detection/           # 快速检测
│  │  ├─ emergency/           # 应急命令页
│  │  ├─ settings/            # 设置持久化与设置页逻辑
│  │  ├─ ai/                  # AI 服务封装
│  │  └─ ...
│  └─ main.ts                 # 前端主入口
├─ src-python/                # FastAPI 后端
│  ├─ app/
│  │  ├─ routers/             # API 路由
│  │  ├─ services/            # 业务服务
│  │  ├─ models/              # 数据模型
│  │  └─ utils/               # 工具函数
│  ├─ run.py                  # Python 启动入口
│  └─ requirements.txt
├─ public/                    # 静态资源
├─ index.html                 # 主页面入口
├─ ssh-terminal.html          # 独立 SSH 终端窗口入口
├─ container-terminal.html    # 占位页面，容器终端未完整接回
└─ lovely/                    # 独立示例项目，不是主应用
```

## 前端核心模块

### 应用入口

- `src/main.ts`
- `src/modules/core/app.ts`
- `src/modules/core/stateManager.ts`

职责：

- 初始化应用
- 创建主 UI
- 管理全局状态
- 注册全局函数
- 初始化设置、远程操作、终端等子系统

### UI 渲染

- `src/modules/ui/modernUIRenderer.ts`

职责：

- 渲染标题栏、侧边栏、工作区、状态栏
- 根据 `currentPage` 输出不同页面 HTML
- 组织 dashboard、system-info、remote-operations、quick-detection、log-analysis、settings、ai-chat 等页面

### SSH 与终端

- `src/components/SSHTerminal.vue`
- `src/modules/ssh/sshTerminalManager.ts`
- `src/modules/ssh/sshManager.ts`
- `src/modules/remote/sshConnectionManager.ts`

职责：

- 维护 SSH 连接配置
- 维护当前活动连接状态
- 提供多标签终端
- 处理 xterm 输入输出、补全、命令提示、AI 助手、重连等

说明：

当前仓库里存在两套 SSH 连接管理逻辑：

- `sshManager.ts` 更偏配置管理与认证连接
- `remote/sshConnectionManager.ts` 更偏当前活动连接状态与页面联动

这是当前代码结构中的一个重要历史遗留点。

### SFTP 与远程操作

- `src/modules/remote/sftpManager.ts`
- `src/modules/remote/remoteOperationsManager.ts`

职责：

- 维护当前远程路径
- 拉取并排序远程文件列表
- 处理目录导航
- 驱动远程操作页中的 SFTP UI 刷新

### 系统信息

- `src/modules/system/systemInfoManager.ts`

职责：

- 通过 SSH 在目标 Linux 主机上执行命令
- 解析命令输出为结构化数据
- 供仪表盘和详细系统信息页使用

这部分不是纯后端结构化接口模式，而是“后端执行命令，前端解析文本结果”的实现方式。

### 设置与 AI

- `src/modules/settings/settingsManager.ts`
- `src/modules/settings/settingsPageManager.ts`
- `src/modules/ai/aiService.ts`

职责：

- 读写本地设置与后端 `settings.json`
- 管理字体、主题、AI 提供商配置
- 提供 AI 连接测试、解决方案生成、日志解释、终端 AI 辅助

## 启动方式

### 1. 安装前端依赖

```bash
npm install
```

### 2. 安装 Python 依赖

推荐在 `src-python/` 下使用虚拟环境。

```bash
cd src-python
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 启动 Python 后端

在仓库根目录可直接运行：

```bash
npm run python-backend
```

或手动运行：

```bash
cd src-python
python run.py
```

默认后端地址：

```text
http://127.0.0.1:3001
```

### 4. 启动前端开发服务器

在仓库根目录运行：

```bash
npm run dev
```

默认前端地址：

```text
http://127.0.0.1:1420
```

## 构建

```bash
npm run build
```

该命令会先执行 `vue-tsc --noEmit`，再执行 Vite 生产构建。

## 主要页面入口

- 主应用：`index.html`
- 独立 SSH 终端：`ssh-terminal.html`
- 容器终端占位页：`container-terminal.html`

Vite 已按多页面应用配置这些入口，见：

- `vite.config.ts`

## 开发注意事项

### 1. 文档与代码可能不一致

历史文档中很多描述仍保留 Rust/Tauri 版本痕迹。开发时请以当前代码为准：

- Python 后端是当前有效后端
- `src/shims/@tauri-apps/api/*` 是兼容层，不是完整原生 Tauri 环境

### 2. 主界面依赖大量全局函数

很多交互不是 Vue 事件流，而是：

- 渲染器输出 HTML
- HTML 上的 `onclick`
- 转到 `window.xxx`
- 再调用具体 manager

修改页面功能时，需要同时检查：

- `modernUIRenderer.ts`
- `src/main.ts`
- 对应 manager / modal / context menu

### 3. 终端是最独立、最复杂的前端模块

如果你要改终端相关功能，优先看：

- `src/components/SSHTerminal.vue`
- `src/modules/ssh/sshTerminalManager.ts`

### 4. 仓库中有非主链内容

以下内容会增加阅读噪音，但不属于当前主应用主链：

- `lovely/` 子项目
- `public/payloader/` 内嵌产物
- Python `__pycache__`
- 本地虚拟环境 `.venv/`

## 已知问题

基于当前代码结构，可见的几个问题：

- README 与实现长期漂移
- SSH 连接存在双管理路径
- 主页面不是完全组件化，维护成本较高
- `container-terminal.html` 当前只是占位页
- 部分 API/模块命名仍保留历史 Tauri 语义

## 适合的后续整理方向

如果后续要继续维护这个项目，建议优先做这几件事：

1. 统一 SSH 连接状态管理，去掉双轨逻辑
2. 将主页面逐步从字符串模板迁移到 Vue 组件
3. 清理历史文档与失效入口
4. 区分主应用代码和示例/实验目录
5. 为核心流程补基础测试

## License

仓库当前包含 `LICENSE` 文件，请以仓库实际 license 内容为准。
