# LovelyERes - Python FastAPI 后端

## 📖 说明

本项目已将从原始的 **Rust + Tauri** 后端迁移到 **Python FastAPI**，同时保留了所有前端功能。

### 架构变化

- ✅ **移除**: Rust + Tauri 后端
- ✅ **新增**: Python FastAPI 后端
- ✅ **保留**: 所有前端功能 (SSH、SFTP、Docker、系统监控等)
- ✅ **API 适配**: 前端通过 `src/config/invoke-adapter.ts` 调用后端 API

## 🔧 环境要求

- **Node.js** (v18+)
- **Python** (v3.8+)
- **npm** 或 **pnpm**

## 📦 安装步骤

### 1. 安装前端依赖

```bash
npm install
```

### 2. 安装 Python 后端依赖

```bash
cd src-python
pip install -r requirements.txt
```

**依赖说明**:
- `fastapi` - Web 框架
- `uvicorn` - ASGI 服务器
- `asyncssh` - 异步 SSH 库
- `paramiko` - SSH 连接备用库
- `cryptography` - 加密支持
- `pydantic` - 数据验证
- `aiofiles` - 异步文件操作

## 🚀 运行步骤

### 开发模式

1. **启动 Python 后端** (终端 1)
   ```bash
   cd src-python
   python run.py
   ```
   
   后端将运行在 `http://127.0.0.1:3001`

2. **启动前端开发服务器** (终端 2)
   ```bash
   npm run dev
   ```
   
   前端将运行在 `http://localhost:5173`

### 生产模式

1. **构建前端**
   ```bash
   npm run build
   ```

2. **启动 Python 后端**
   ```bash
   cd src-python
   python run.py
   ```

3. **配置静态文件服务**
   
   后端会自动提供 `dist/` 目录的静态文件，或者使用其他静态服务器（如 nginx）托管 `dist/` 目录。

## 📡 API 端点

### REST API

- `POST /api/invoke` - 统一的 API 调用端点
- `GET /api/health` - 健康检查

### WebSocket

- `ws://127.0.0.1:3001/ws/terminal/{terminal_id}` - 实时终端通信
- `ws://127.0.0.1:3001/ws/events` - 事件推送通道

## 🔍 主要功能模块

### SSH 连接管理
- SSH 连接建立/断开
- 密码/密钥认证
- 终端会话管理
- 命令执行

### SFTP 文件操作
- 文件列表/读取/写入
- 文件上传/下载
- 压缩/解压
- 权限管理

### Docker 管理
- 容器列表/启停
- 日志查看
- 文件操作
- 命令执行

### 系统监控
- 系统信息采集
- 进程管理
- 网络监控
- 用户管理

### 安全检测
- 端口扫描检测
- 后门检测
- 日志分析
- 基线检查

## ⚠️ 注意事项

1. **后端服务必须先行启动**
   - 确保 Python 后端 (`http://127.0.0.1:3001`) 在前端启动前已运行
   - 前端会调用后端的 API 进行所有系统交互

2. **CORS 配置**
   - 开发模式下，后端允许所有来源的 CORS 请求
   - 生产环境应配置适当的 CORS 策略

3. **连接问题排查**
   - 检查 Python 后端是否正常运行
   - 检查端口 3001 是否被占用
   - 查看后端日志输出

4. **WebSocket 连接**
   - 终端实时通信依赖 WebSocket
   - 确保防火墙未阻止 WebSocket 连接

## 📝 开发指南

### 添加新的 API 端点

1. 在 `src-python/app/routers/api.py` 中添加路由
2. 在 `src-python/app/services/` 中实现业务逻辑
3. 在前端 `src/config/invoke-adapter.ts` 中添加 API 映射
4. 在 UI 中调用新 API

### 调试技巧

- **后端日志**: 查看终端输出的日志信息
- **前端调试**: 使用浏览器开发者工具
- **网络监控**: 检查 Network 面板的 API 调用和 WebSocket 连接

## 🔄 从 Tauri 迁移

如果你之前使用过 Tauri 版本，请注意以下变化：

| Tauri | Python FastAPI |
|-------|----------------|
| `invoke('command_name')` | `invoke('command_name')` (通过适配器) |
| Rust 后端 | Python 后端 |
| `tauri.conf.json` | 无配置文件 |
| `src-tauri/` | `src-python/` |
| `cargo build` | `pip install` |

## 🆘 常见问题

### Q: 后端启动失败？
A: 检查 Python 版本 (>=3.8) 和依赖是否安装完整

### Q: 前端无法连接后端？
A: 确认后端运行在 `http://127.0.0.1:3001`，检查 CORS 配置

### Q: SSH 连接失败？
A: 检查目标服务器地址、端口、用户名和密码/密钥

### Q: WebSocket 连接断开？
A: 检查网络连接，确保防火墙未阻止 WebSocket

---

**更多信息请查看 [README.md](README.md) 和 [AGENTS.md](AGENTS.md)**
