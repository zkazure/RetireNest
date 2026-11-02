"""strategy：预设人生策略。

`presets` 定义五个可对比的活法，`apply` 把它们套到用户画像上，得到只改了
少数参数的变体；比较与仿真由 `lifecycle` 负责。
"""

from strategy.apply import apply
from strategy.errors import StrategyError
from strategy.presets import PRESET_IDS, PRESETS, Preset, get_preset

__all__ = ["PRESETS", "PRESET_IDS", "Preset", "StrategyError", "apply", "get_preset"]
