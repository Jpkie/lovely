"""LovelyRes Python 后端启动入口"""

import os

import uvicorn


if __name__ == "__main__":
    # Windows 某些环境下 uvicorn reload 会触发多进程/命名管道权限错误，
    # 默认关闭 reload，需要时再通过环境变量显式开启。
    reload_enabled = os.getenv("LOVELY_PY_RELOAD", "").lower() in {"1", "true", "yes"}

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=3001,
        reload=reload_enabled,
        log_level="info",
    )
