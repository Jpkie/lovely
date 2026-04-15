# LovelyRes Development Guide

本项目是 LovelyRes 代码库，一个使用 **Python FastAPI** 后端和 **Vue 3 + TypeScript** 前端构建的跨平台 Linux 应急响应工具。

## 🛠 项目结构

- **Frontend**: `src/` (Vue 3, TypeScript, Vite)
  - Entry point: `src/main.ts`
  - Core logic: `src/modules/`
  - Styles: `src/css/`, `src/styles/`
  - Config & API Adapter: `src/config/`
- **Backend**: `src-python/` (Python FastAPI)
  - Main app: `src-python/app/main.py`
  - Routers: `src-python/app/routers/`
  - Services: `src-python/app/services/`
  - Models: `src-python/app/models/`
  - Utils: `src-python/app/utils/`

## 🚀 构建与测试命令

### 环境要求

- Node.js (v18+) & pnpm/npm
- Python (v3.8+)

### 命令

| Action | Command | Description |
|--------|---------|-------------|
| **Dev** | `npm run dev` | 启动前端开发服务器 (需先启动 Python 后端) |
| **Python Backend** | `cd src-python && python run.py` | 启动 Python FastAPI 后端 |
| **Build** | `npm run build` | 构建生产应用 |
| **Lint** | `npm run build` | 运行 `vue-tsc` (类型检查) & Vite 构建 |
| **Test** | *参见下方说明* | 当前未配置专用测试运行器 |

> **测试说明**: 项目当前缺乏标准化测试套件。添加测试时，前端推荐使用 **Vitest** (Vue/TS)，后端推荐使用 **pytest** (Python)。

## 🎨 代码风格与规范

### 通用规范

- **缩进**: 2 个空格 (前端), 4 个空格 (Python)
- **行尾**: LF
- **文件命名**:
  - TS/JS: `camelCase.ts` (例如：`stateManager.ts`)
  - Vue: `PascalCase.vue` (例如：`SSHTerminal.vue`)
  - Python: `snake_case.py`
- **注释**: 简洁的解释性"为什么"注释。公共 API 使用 JSDoc/Python Docstring

### 前端 (Vue/TS)

- **框架**: Vue 3 Composition API (`<script setup lang="ts">`)
- **导入**:
  - 分组导入：外部库 (vue, @tauri-apps) -> 内部模块 -> 样式
  - 避免 `src/modules/` 中的循环依赖
- **类型**: 严格 TypeScript。尽可能避免使用 `any`
  - 在 `src/types.ts` 或本地模块文件中定义接口
- **状态管理**: 使用 `StateManager` 类模式 (可观察/响应式) 或 Vue 的 `ref/reactive`
- **UI 组件**: 旧代码中存在手动 DOM 操作 (例如 `document.createElement`)，但新功能应使用 Vue 组件
- **Async/Await**: 对 API 调用始终使用 async/await

### 后端 (Python FastAPI)

- **框架**: FastAPI, Pydantic
- **异步**: 大量使用 `asyncio` 和 `async/await`
- **SSH**: 使用 `asyncssh` 和 `paramiko`
- **错误处理**: 使用 Python 异常处理，返回适当的 HTTP 状态码
- **类型提示**: 使用 Python 类型提示 (Type Hints)

### 🛡 安全与最佳实践

- **机密信息**: 永远不要提交 `.env`、私钥或凭证
- **输入验证**: 在 Python 后端验证所有来自前端的输入
- **CORS**: 配置适当的 CORS 策略
- **错误处理**: 优雅地处理错误，不泄露敏感信息

## 🤖 Agent 使用说明

- **修改 UI**: 在创建新 UI 之前，检查 `src/modules/ui/` 中是否已存在渲染器 (例如 `modernUIRenderer.ts`)
- **添加功能**:
  1. 在 `src-python/app/routers/api.py` 中定义 FastAPI 路由
  2. 在 `src-python/app/services/` 中实现业务逻辑
  3. 在前端通过 HTTP API 调用 (使用 `fetch` 或 `axios`)
  4. 更新 UI 以触发 API 调用
- **重构**: 注意全局 window 对象 (`(window as any).app`)。旧代码严重依赖它们
- **API 调用**: 前端使用 `src/config/invoke-adapter.ts` 作为统一的 API 调用接口

## 📝 开发注意事项

### 前端开发

- 使用 Vite 进行快速开发和热重载
- 代码已配置生产环境混淆 (vite-plugin-bundle-obfuscator)
- 多页面应用配置 (index.html, ssh-terminal.html, container-terminal.html)

### 后端开发

- FastAPI 服务器运行在 `http://127.0.0.1:3001`
- WebSocket 支持终端实时通信
- 所有业务逻辑在 `src-python/app/services/` 中实现

### 前后端通信

- 前端通过 HTTP API 与后端通信
- WebSocket 用于实时终端输出
- 使用 `src/config/invoke-adapter.ts` 作为统一的 API 适配器
