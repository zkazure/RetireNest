"""页面清单端点。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from api.errors import ApiError
from pages import PAGES, PageError, resolve

router = APIRouter(prefix="/api/pages", tags=["pages"])


@router.get("/{page_id}")
def get_page(page_id: str) -> dict[str, Any]:
    page = PAGES.get(page_id)
    if page is None:
        raise ApiError(404, "UNKNOWN_PAGE", f"未知页面：{page_id}")
    try:
        return resolve(page)
    except PageError as exc:
        raise ApiError(500, "PAGE_DEFINITION_INVALID", str(exc)) from exc
