"""pages：页面清单。

页面清单把“问什么”留在命令 manifest 里，只补充分组、顺序、开关与执行清单。
解析结果由 `GET /api/pages/{page_id}` 提供给前端。
"""

from pages.models import (
    PageError,
    PageExecution,
    PageField,
    PageManifest,
    PageRule,
    PageSection,
    PageToggle,
)
from pages.resolve import resolve
from pages.lifecycle import MANIFEST as LIFECYCLE_PAGE
from pages.lifecycle import PAGES as LIFECYCLE_PAGES
from pages.retirement import MANIFEST as RETIREMENT_PAGE
from pages.retirement import PAGES as RETIREMENT_PAGES

PAGES: dict = {**RETIREMENT_PAGES, **LIFECYCLE_PAGES}
"""当前可用的页面。"""

__all__ = [
    "LIFECYCLE_PAGE",
    "PAGES",
    "RETIREMENT_PAGE",
    "PageError",
    "PageExecution",
    "PageField",
    "PageManifest",
    "PageRule",
    "PageSection",
    "PageToggle",
    "resolve",
]
