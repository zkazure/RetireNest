"""接口层错误类型与固定错误响应。"""

from __future__ import annotations

from plan.models import FieldError


class ApiError(Exception):
    """带 HTTP 状态码和业务 code 的可预期错误。"""

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        field_errors: list[FieldError] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.field_errors = field_errors or []


def validation_error(field_errors: list[FieldError]) -> ApiError:
    return ApiError(
        status=422,
        code="VALIDATION_ERROR",
        message="请检查填写信息。",
        field_errors=field_errors,
    )


def schema_mismatch() -> ApiError:
    return ApiError(
        status=409,
        code="SCHEMA_VERSION_MISMATCH",
        message="表单模板版本不匹配，请刷新页面后重试。",
    )


def calculation_error() -> ApiError:
    return ApiError(
        status=500,
        code="CALCULATION_ERROR",
        message="测算过程中出现错误，请稍后重试。",
    )
