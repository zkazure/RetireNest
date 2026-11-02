"""手动抓取银行活期挂牌利率，输出候选值供人工核对。

用法（工作目录为 src/）：

    uv run python tools/fetch_rates.py

页面用 r.jina.ai 渲染后再解析，因为这个代理会执行 JS；只有本脚本联网，
deposit 包本身不依赖网络。抓到的是候选值，核对银行公告后手动改
deposit/rates.py 的 SNAPSHOT，脚本不会自动写文件。
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

RENDER_PROXY = "https://r.jina.ai/"
TIMEOUT_SECONDS = 45


@dataclass(frozen=True, slots=True)
class Source:
    bank: str
    url: str
    pattern: str


SOURCES: tuple[Source, ...] = (
    # 「（一）活期 0.05」，工行利率表里活期后紧跟数值
    Source(
        bank="工商银行",
        url="https://www.icbc.com.cn/column/1438058341686722587.html",
        pattern=r"活期\s*[^\d]{0,6}(\d+\.\d+)",
    ),
    # 「一、活期存款 0.05」，建行把标题和数值连着渲染
    Source(
        bank="建设银行",
        url="https://wealth.ccb.com/chn/personal/interestv3/rmbdeposit.shtml",
        pattern=r"活期存款\*{0,4}\s*(\d+\.\d+)",
    ),
    # 招行是 markdown 表格：| 活期 | 0.0500 | ...，取第一列后面的数值
    Source(
        bank="招商银行",
        url="https://fin.paas.cmbchina.com/fininfo/interestrate",
        pattern=r"\|\s*活期\s*\|\s*(\d+\.\d+)",
    ),
)


def fetch(url: str) -> str:
    # 别带浏览器 User-Agent：渲染代理会把它当爬虫直接 403
    request = urllib.request.Request(RENDER_PROXY + url)
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_rate(text: str, pattern: str) -> Decimal:
    match = re.search(pattern, text)
    if match is None:
        raise RuntimeError("页面里没找到活期利率，可能改版或被拦截")
    percent = Decimal(match.group(1))
    # 页面给的是百分数（0.05 表示 0.05%），换成计算用的年利率小数
    return (percent / 100).quantize(Decimal("0.000001"))


def main() -> int:
    failures = 0
    for source in SOURCES:
        try:
            rate = parse_rate(fetch(source.url), source.pattern)
        except (urllib.error.URLError, TimeoutError, RuntimeError, InvalidOperation) as exc:
            failures += 1
            print(f"{source.bank}: 抓取失败 —— {exc}")
            continue
        percent = (rate * 100).normalize()
        print(f"{source.bank}: 活期 {percent}%  ({source.url})")
    if failures:
        print(f"\n{failures} 家失败，失败的一家都不要手工补数，重试或换个来源。")
    print("\n核对银行公告后，把结果抄进 deposit/rates.py 的 SNAPSHOT，并更新 fetched_at。")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
