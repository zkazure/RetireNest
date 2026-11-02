"""养老金计算的错误类型。

单独成模块而不复用 deposit.errors：养老金与存款收益是两个领域，共用一个错误类
会让调用方分不清失败到底出在哪一侧。
"""

from __future__ import annotations


class PensionError(ValueError):
    """养老金参数不合法或口径不满足时抛出。"""
