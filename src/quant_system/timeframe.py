from __future__ import annotations

import pandas as pd

from quant_system.models import normalize_ohlcv


_FREQUENCY_ALIASES = {
    "daily": "D",
    "day": "D",
    "1d": "D",
    "weekly": "W-FRI",
    "week": "W-FRI",
    "1wk": "W-FRI",
    "monthly": "M",
    "month": "M",
    "1mo": "M",
}


def resample_ohlcv(prices: pd.DataFrame, frequency: str = "daily") -> pd.DataFrame:
    """Resample one security's OHLCV data to daily, weekly, or monthly bars."""

    data = normalize_ohlcv(prices)
    rule = _FREQUENCY_ALIASES.get(str(frequency).strip().lower())
    if rule is None:
        raise ValueError("frequency must be one of daily, weekly, monthly, 1d, 1wk, 1mo.")
    if rule == "D":
        return data.copy()

    grouped = data.set_index("date").resample(rule)
    resampled = grouped.agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    ).dropna(subset=["open", "high", "low", "close"])
    if "symbol" in data.columns:
        resampled["symbol"] = data["symbol"].dropna().iloc[-1]
    if "market" in data.columns:
        resampled["market"] = data["market"].dropna().iloc[-1]
    resampled = resampled.reset_index()
    return normalize_ohlcv(resampled)
