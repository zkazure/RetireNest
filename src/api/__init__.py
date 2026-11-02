"""api：RetireNest 的 FastAPI 接入层。

启动：

    cd src
    uv run uvicorn api.app:app --host 127.0.0.1 --port 8000

接口：

    GET  /api/pages/{page_id}
    GET  /api/commands
    POST /api/commands/{command_id}
"""
