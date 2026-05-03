from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd

from quant_system.analysis.indicators import add_indicators
from quant_system.models import normalize_ohlcv


class Strategy(ABC):
    name = "base"

    @abstractmethod
    def generate_signals(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Return a DataFrame with at least target_weight."""


class MovingAverageCrossStrategy(Strategy):
    name = "ma"

    def __init__(self, short_window: int = 20, long_window: int = 60, max_weight: float = 1.0):
        if short_window >= long_window:
            raise ValueError("short_window must be smaller than long_window.")
        self.short_window = short_window
        self.long_window = long_window
        self.max_weight = max_weight

    def generate_signals(self, prices: pd.DataFrame) -> pd.DataFrame:
        data = add_indicators(prices, ma_windows=(self.short_window, self.long_window))
        short_ma = data[f"sma_{self.short_window}"]
        long_ma = data[f"sma_{self.long_window}"]
        target = np.where(short_ma > long_ma, self.max_weight, 0.0)
        return _signal_frame(data, target, reason=np.where(short_ma > long_ma, "short_ma_above_long_ma", "flat"))


class RSIMeanReversionStrategy(Strategy):
    name = "rsi"

    def __init__(self, oversold: float = 30.0, overbought: float = 70.0, max_weight: float = 1.0):
        if oversold >= overbought:
            raise ValueError("oversold must be smaller than overbought.")
        self.oversold = oversold
        self.overbought = overbought
        self.max_weight = max_weight

    def generate_signals(self, prices: pd.DataFrame) -> pd.DataFrame:
        data = add_indicators(prices)
        weights: list[float] = []
        reasons: list[str] = []
        position = 0.0
        for value in data["rsi"]:
            if value <= self.oversold:
                position = self.max_weight
                reasons.append("rsi_oversold")
            elif value >= self.overbought:
                position = 0.0
                reasons.append("rsi_overbought")
            else:
                reasons.append("hold")
            weights.append(position)
        return _signal_frame(data, weights, reason=reasons)


class DonchianBreakoutStrategy(Strategy):
    name = "breakout"

    def __init__(self, window: int = 20, max_weight: float = 1.0):
        if window < 2:
            raise ValueError("window must be at least 2.")
        self.window = window
        self.max_weight = max_weight

    def generate_signals(self, prices: pd.DataFrame) -> pd.DataFrame:
        data = normalize_ohlcv(prices)
        previous_high = data["high"].rolling(self.window, min_periods=max(2, self.window // 2)).max().shift(1)
        previous_low = data["low"].rolling(self.window, min_periods=max(2, self.window // 2)).min().shift(1)
        weights: list[float] = []
        reasons: list[str] = []
        position = 0.0
        for close, high_break, low_break in zip(data["close"], previous_high, previous_low):
            if pd.notna(high_break) and close > high_break:
                position = self.max_weight
                reasons.append("donchian_breakout")
            elif pd.notna(low_break) and close < low_break:
                position = 0.0
                reasons.append("donchian_exit")
            else:
                reasons.append("hold")
            weights.append(position)
        return _signal_frame(data, weights, reason=reasons)


def build_strategy(name: str, **kwargs: object) -> Strategy:
    normalized = name.strip().lower()
    if normalized in {"ma", "moving_average", "moving-average"}:
        return MovingAverageCrossStrategy(
            short_window=int(kwargs.get("short_window", 20)),
            long_window=int(kwargs.get("long_window", 60)),
            max_weight=float(kwargs.get("max_weight", 1.0)),
        )
    if normalized in {"rsi", "mean_reversion", "mean-reversion"}:
        return RSIMeanReversionStrategy(
            oversold=float(kwargs.get("oversold", 30.0)),
            overbought=float(kwargs.get("overbought", 70.0)),
            max_weight=float(kwargs.get("max_weight", 1.0)),
        )
    if normalized in {"breakout", "donchian"}:
        return DonchianBreakoutStrategy(
            window=int(kwargs.get("window", kwargs.get("long_window", 20))),
            max_weight=float(kwargs.get("max_weight", 1.0)),
        )
    raise ValueError(f"Unknown strategy: {name}")


def _signal_frame(data: pd.DataFrame, target: object, reason: object) -> pd.DataFrame:
    signals = pd.DataFrame(
        {
            "date": data["date"],
            "symbol": data.get("symbol", ""),
            "market": data.get("market", ""),
            "close": data["close"],
            "target_weight": pd.Series(target, index=data.index, dtype=float).clip(0.0, 1.0),
            "reason": reason,
        },
        index=data.index,
    )
    return signals

