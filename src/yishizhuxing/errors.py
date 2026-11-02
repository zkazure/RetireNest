"""本模块的异常类型。

LivingCostError 继承 ValueError，因此已经写成 `except ValueError` 的调用方
不需要改动就能捕获它；需要区分错误来源时再单独捕获 LivingCostError。
"""


class LivingCostError(ValueError):
    """输入不合法，或参数之间不满足约束时抛出。"""
