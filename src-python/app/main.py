"""LovelyRes Python 后端 - FastAPI 主应用

从 Rust Tauri 后端迁移到 Python FastAPI
"""

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.routers.api import router, init_state, _ssh_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    init_state()
    print("LovelyRes Python 后端已启动")
    yield
    # 关闭时清理
    if _ssh_manager and _ssh_manager.is_connected():
        await _ssh_manager.disconnect()
    print("LovelyRes Python 后端已关闭")


app = FastAPI(
    title="LovelyRes API",
    description="LovelyRes - Linux 应急响应工具 Python 后端",
    version="0.55.0",
    lifespan=lifespan,
)

# CORS：与 allow_origins=["*"] 组合时不可启用 allow_credentials，否则浏览器会拒绝
#（ACAO 为 * 时不能带 Access-Control-Allow-Credentials: true），前端 fetch 表现为 Failed to fetch。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router)


# ==================== WebSocket 端点 ====================

@app.websocket("/ws/terminal/{terminal_id}")
async def websocket_terminal(websocket: WebSocket, terminal_id: str):
    """WebSocket 终端 - 用于实时终端输入/输出"""
    await websocket.accept()
    print(f"WebSocket 终端连接: {terminal_id}")

    if not _ssh_manager or not _ssh_manager.is_connected():
        await websocket.close(code=1001, reason="没有活动的 SSH 连接")
        return

    # 创建终端会话
    try:
        await _ssh_manager.create_terminal_session(terminal_id, 80, 24)
    except Exception as e:
        await websocket.close(code=1001, reason=str(e))
        return

    # 启动输出读取任务
    async def read_output():
        """持续读取终端输出并发送到 WebSocket"""
        try:
            while True:
                data = await _ssh_manager.read_terminal_output(terminal_id)
                if data:
                    await websocket.send_bytes(data)
                await asyncio.sleep(0.01)
        except Exception:
            pass

    output_task = asyncio.create_task(read_output())

    try:
        while True:
            # 接收 WebSocket 消息
            data = await websocket.receive_bytes()
            await _ssh_manager.send_terminal_input(terminal_id, data)
    except WebSocketDisconnect:
        print(f"WebSocket 终端断开: {terminal_id}")
    except Exception as e:
        print(f"WebSocket 终端错误: {e}")
    finally:
        output_task.cancel()
        await _ssh_manager.close_terminal_session(terminal_id)


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket 事件通道 - 用于服务端推送事件"""
    await websocket.accept()
    print("WebSocket 事件通道连接")

    try:
        while True:
            # 保持连接，等待客户端消息
            data = await websocket.receive_text()
            # 可以处理客户端发来的事件
            msg = json.loads(data) if data else {}
            event_type = msg.get("type", "")

            if event_type == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        print("WebSocket 事件通道断开")
    except Exception as e:
        print(f"WebSocket 事件通道错误: {e}")


# ==================== 健康检查 ====================

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "service": "LovelyRes Python Backend",
        "version": "0.55.0",
        "ssh_connected": _ssh_manager.is_connected() if _ssh_manager else False,
    }
