"""资产配置组合的测试。"""

from __future__ import annotations

import pytest

from portfolio import ASSET_CLASSES, Allocation, PortfolioError, combine


def test_默认配比合法():
    allocation = Allocation()
    assert sum(allocation.weights().values()) == pytest.approx(1.0)


def test_单档配比等于该档假设():
    for key, asset in ASSET_CLASSES.items():
        weights = {"high": 0.0, "mid": 0.0, "low": 0.0}
        weights[key] = 1.0
        result = combine(weights)
        assert result.annual_return_pct == pytest.approx(asset.annual_return_pct)
        assert result.volatility_pct == pytest.approx(asset.volatility_pct)


def test_组合收益是加权平均():
    result = combine({"high": 0.5, "mid": 0.5, "low": 0.0})
    expected = (ASSET_CLASSES["high"].annual_return_pct + ASSET_CLASSES["mid"].annual_return_pct) / 2
    assert result.annual_return_pct == pytest.approx(expected)


def test_股债组合波动低于加权平均():
    result = combine({"high": 0.5, "mid": 0.5, "low": 0.0})
    weighted = (
        ASSET_CLASSES["high"].volatility_pct + ASSET_CLASSES["mid"].volatility_pct
    ) / 2
    assert result.volatility_pct < weighted


def test_权益比例越高收益越高():
    conservative = combine({"high": 0.2, "mid": 0.4, "low": 0.4})
    aggressive = combine({"high": 0.6, "mid": 0.3, "low": 0.1})
    assert aggressive.annual_return_pct > conservative.annual_return_pct
    assert aggressive.volatility_pct > conservative.volatility_pct


@pytest.mark.parametrize(
    "weights",
    [
        {"high": 0.5, "mid": 0.4, "low": 0.4},
        {"high": -0.1, "mid": 0.6, "low": 0.5},
        {"high": 0.5, "mid": 0.5, "low": 0.0, "unknown": 0.0},
    ],
)
def test_非法配比报错(weights):
    with pytest.raises(PortfolioError):
        combine(weights)


def test_配比可以省略档位():
    result = combine({"high": 1.0})
    assert result.annual_return_pct == pytest.approx(ASSET_CLASSES["high"].annual_return_pct)


def test_配比对象校验():
    with pytest.raises(PortfolioError):
        Allocation(high=0.5, mid=0.5, low=0.5)
    with pytest.raises(PortfolioError):
        Allocation(high=-0.1, mid=0.6, low=0.5)


def test_组合波动非负():
    for high in (0.0, 0.3, 0.7, 1.0):
        result = combine({"high": high, "mid": 1 - high, "low": 0.0})
        assert result.volatility_pct >= 0
