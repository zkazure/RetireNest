"""HTTP 请求与错误响应的 Pydantic 模型。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class PlanRequest(BaseModel):
    """前端提交的规划请求；values 是动态模板收集的扁平对象。"""

    model_config = ConfigDict(extra="forbid")

    template_id: str
    schema_version: str
    values: dict[str, Any]


class FieldErrorModel(BaseModel):
    field: str
    message: str


class PlanErrorResponse(BaseModel):
    code: str
    message: str
    field_errors: list[FieldErrorModel] | None = None
