from __future__ import annotations

import numpy as np
import pandas as pd

from quant_system.models import normalize_ohlcv


def add_indicators(
    prices: pd.DataFrame,
    ma_windows: tuple[int, ...] = (5, 10, 20, 60, 120),
    rsi_window: int = 14,
    atr_window: int = 14,
) -> pd.DataFrame:
    """Add common technical indicators to a price frame."""

    data = normalize_ohlcv(prices)
    close = data["close"]
    high = data["high"]
    low = data["low"]

    data["return"] = close.pct_change()
    data["log_return"] = np.log(close / close.shift(1))

    for window in sorted(set(ma_windows)):
        min_periods = max(2, min(window, max(2, len(data) // 3)))
        data[f"sma_{window}"] = close.rolling(window=window, min_periods=min_periods).mean()
        data[f"ema_{window}"] = close.ewm(span=window, adjust=False, min_periods=min_periods).mean()
        data[f"momentum_{window}"] = close.pct_change(window)
        data[f"volatility_{window}"] = data["return"].rolling(window=window, min_periods=min_periods).std() * np.sqrt(252)

    data["rsi"] = rsi(close, window=rsi_window)
    macd_line, signal_line, histogram = macd(close)
    data["macd"] = macd_line
    data["macd_signal"] = signal_line
    data["macd_hist"] = histogram

    middle, upper, lower = bollinger_bands(close)
    data["bb_mid"] = middle
    data["bb_upper"] = upper
    data["bb_lower"] = lower
    data["bb_width"] = (upper - lower) / middle.replace(0, np.nan)
    data["atr"] = atr(high=high, low=low, close=close, window=atr_window)
    data["drawdown"] = close / close.cummax() - 1.0
    return data


def rsi(close: pd.Series, window: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    average_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=max(2, window // 2)).mean()
    average_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=max(2, window // 2)).mean()
    relative_strength = average_gain / average_loss.replace(0, np.nan)
    result = 100 - (100 / (1 + relative_strength))
    return result.fillna(50.0).clip(0, 100)


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    fast_ema = close.ewm(span=fast, adjust=False).mean()
    slow_ema = close.ewm(span=slow, adjust=False).mean()
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line, macd_line - signal_line


def bollinger_bands(
    close: pd.Series,
    window: int = 20,
    num_std: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    min_periods = max(2, min(window, max(2, len(close) // 3)))
    middle = close.rolling(window=window, min_periods=min_periods).mean()
    deviation = close.rolling(window=window, min_periods=min_periods).std()
    upper = middle + num_std * deviation
    lower = middle - num_std * deviation
    return middle, upper, lower


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    min_periods = max(2, min(window, max(2, len(close) // 3)))
    return true_range.rolling(window=window, min_periods=min_periods).mean()

