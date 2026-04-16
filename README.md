# LovelyRes

Linux 应急响应工具 | Linux Emergency Response Tool

## 简介

LovelyRes 是一款专为 Linux 系统设计的应急响应工具，提供 SSH 远程连接、终端管理、文件操作、安全检测、日志分析和 AI 智能辅助等功能，帮助安全人员快速完成主机检测、威胁分析和事件响应工作。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + TypeScript + Vite |
| 后端 | Python FastAPI |
| 通信 | HTTP API + WebSocket |
| SSH | asyncssh / paramiko |

## 功能特性

### 远程连接
- SSH 连接管理（支持密码/密钥认证）
- 实时终端仿真（WebSocket 实时回显）
- SFTP 文件传输与管理

### 系统检测
- 端口安全扫描
- 后门痕迹检测
- 用户账户审计
- SSH 安全审计
- 进程/服务分析
- 网络连接检查
- 防火墙状态验证
- 启动项检查
- Cron 任务审计

### 日志分析
- 日志文件查看与搜索
- 异常行为模式识别

### AI 智能助手
- LLM 驱动的安全事件分析
- 智能威胁研判
- 自动修复建议

### 应急响应
- 快速检测命令集
- 一键处置脚本
- 事件时间线构建
- 安全基线加固

## 项目结构

```
LovelyERes/
├── src/                    # Vue 3 前端源码
│   ├── modules/            # 功能模块
│   │   ├── ai/             # AI 智能助手
│   │   ├── auth/           # 认证模块
│   │   ├── core/           # 核心逻辑
│   │   ├── crypto/         # 加密服务
│   │   ├── detection/      # 检测功能
│   │   ├── emergency/      # 应急响应
│   │   ├── remote/         # 远程操作
│   │   ├── settings/       # 设置管理
│   │   ├── ssh/            # SSH 管理
│   │   ├── system/         # 系统信息
│   │   ├── ui/             # UI 渲染器
│   │   ├── user/           # 用户管理
│   │   └── utils/          # 工具函数
│   ├── components/         # Vue 组件
│   ├── config/             # 配置文件
│   ├── css/                # 样式文件
│   └── styles/             # 附加样式
├── src-python/             # Python FastAPI 后端
│   └── app/
│       ├── models/         # 数据模型
│       ├── routers/        # API 路由
│       ├── services/       # 业务逻辑
│       │   ├── agent/      # AI Agent
│       │   └── agent/skills/ # 技能模块
│       └── utils/          # 工具函数
├── index.html              # 主页面
├── ssh-terminal.html       # SSH 终端页面
└── container-terminal.html # 容器终端页面
```

## 快速开始

### 环境要求

- Node.js >= 18
- Python >= 3.8

### 安装依赖

```bash
# 前端依赖
npm install

# 后端依赖
cd src-python
pip install -r requirements.txt
```

### 启动服务

```bash
# 启动 Python FastAPI 后端（端口 3001）
npm run python-backend

# 启动前端开发服务器
npm run dev
```

### 构建生产版本

```bash
npm run build
```

## 页面说明

| 页面 | 路径 | 用途 |
|------|------|------|
| 主界面 | `/` | 综合应急响应工作台 |
| SSH 终端 | `/ssh-terminal.html` | 独立 SSH 终端 |
| 容器终端 | `/container-terminal.html` | Docker 容器管理 |

## 接口说明

后端 API 运行于 `http://127.0.0.1:3001`，主要端点：

| 端点 | 方法 | 描述 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/*` | * | RESTful API |
| `/ws/terminal/{id}` | WebSocket | 终端回显 |
| `/ws/events` | WebSocket | 事件推送 |

## 安全提示

- 请勿将敏感凭证提交至代码仓库
- 生产环境请务必配置 CORS 策略
- 所有用户输入需在后端进行验证
