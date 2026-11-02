"""RetireNest 的 HTTP 接入层。"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from api.errors import ApiError
from api.schemas import PlanRequest
from api.service import build_plan_response

logger = logging.getLogger(__name__)

app = FastAPI(title="RetireNest 退休规划 API", version="0.1.0")


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    content: dict[str, object] = {"code": exc.code, "message": exc.message}
    if exc.field_errors:
        content["field_errors"] = [
            {"field": error.field, "message": error.message} for error in exc.field_errors
        ]
    return JSONResponse(status_code=exc.status, content=content)


@app.exception_handler(RequestValidationError)
async def request_validation_handler(_: Request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "请求格式无效。",
            "field_errors": [],
        },
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error while building retirement plan", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "code": "CALCULATION_ERROR",
            "message": "测算过程中出现错误，请稍后重试。",
        },
    )


@app.post("/api/retirement/plan")
def create_plan(request: PlanRequest) -> dict[str, object]:
    return build_plan_response(request)


# 生产模式由 run.py 先执行 npm run build，再由这里托管构建产物。
# 挂载放在 API 路由之后，保证 /api 和 /docs 优先匹配。
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
