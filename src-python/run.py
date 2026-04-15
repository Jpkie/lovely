"""LovelyRes Python 后端启动入口"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=3001,
        reload=True,
        log_level="info",
    )
