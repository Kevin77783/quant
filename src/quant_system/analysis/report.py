from __future__ import annotations

import numpy as np
import pandas as pd

from quant_system.analysis.indicators import add_indicators
from quant_system.analysis.performance import calculate_performance
from quant_system.data.providers import DataProvider
from quant_system.models import Security


def analyze_prices(prices: pd.DataFrame, risk_free_rate: float = 0.0) -> dict[str, object]:
    """Build a compact analysis report for one stock."""

    data = add_indicators(prices)
    latest = data.iloc[-1]
    buy_hold_equity = (1.0 + data["return"].fillna(0.0)).cumprod()
    metrics = calculate_performance(buy_hold_equity, risk_free_rate=risk_free_rate)

    trend_score = _trend_score(latest)
    momentum_score = _safe_number(latest.get("momentum_20", np.nan)) * 100
    volatility = _safe_number(latest.get("volatility_20", np.nan))
    rsi_value = _safe_number(latest.get("rsi", 50.0))
    factor_score = _factor_score(latest)

    return {
        "symbol": str(latest.get("symbol", "")),
        "market": str(latest.get("market", "")),
        "date": latest["date"].date().isoformat(),
        "close": float(latest["close"]),
        "trend": _trend_label(trend_score),
        "score": round(float(factor_score), 2),
        "signals": {
            "trend_score": round(float(trend_score), 2),
            "momentum_20_pct": round(float(momentum_score), 2),
            "volatility_20": round(float(volatility), 4),
            "rsi": round(float(rsi_value), 2),
            "macd_hist": round(_safe_number(latest.get("macd_hist", np.nan)), 4),
            "drawdown": round(_safe_number(latest.get("drawdown", np.nan)), 4),
        },
        "performance": {key: round(value, 6) for key, value in metrics.items()},
    }


def screen_universe(
    universe: list[Security],
    provider: DataProvider,
    start: str | None = None,
    end: str | None = None,
    top: int | None = None,
) -> pd.DataFrame:
    """Rank a multi-market universe by trend, momentum, risk and liquidity."""

    rows: list[dict[str, object]] = []
    for security in universe:
        prices = provider.get_history(security.symbol, security.market, start=start, end=end)
        enriched = add_indicators(prices)
        latest = enriched.iloc[-1]
        report = analyze_prices(prices)
        rows.append(
            {
                "symbol": security.symbol,
                "market": security.market.value,
                "name": security.name or "",
                "date": report["date"],
                "close": report["close"],
                "score": report["score"],
                "trend": report["trend"],
                "rsi": report["signals"]["rsi"],
                "momentum_20_pct": report["signals"]["momentum_20_pct"],
                "volatility_20": report["signals"]["volatility_20"],
                "drawdown": report["signals"]["drawdown"],
                "turnover_proxy": float(latest["close"] * latest["volume"]),
            }
        )

    ranked = pd.DataFrame(rows).sort_values(["score", "turnover_proxy"], ascending=[False, False])
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    if top is not None:
        ranked = ranked.head(top)
    return ranked.reset_index(drop=True)


def _factor_score(latest: pd.Series) -> float:
    score = 50.0
    score += _trend_score(latest) * 12.0
    score += np.clip(_safe_number(latest.get("momentum_20", 0.0)) * 100, -15, 15)
    score += np.clip((0.35 - _safe_number(latest.get("volatility_20", 0.35))) * 25, -10, 10)
    score += _rsi_score(_safe_number(latest.get("rsi", 50.0)))
    score += np.clip(_safe_number(latest.get("macd_hist", 0.0)) * 4, -5, 5)
    score += np.clip(_safe_number(latest.get("drawdown", 0.0)) * 40, -12, 0)
    return float(np.clip(score, 0, 100))


def _trend_score(latest: pd.Series) -> float:
    close = _safe_number(latest.get("close", np.nan))
    score = 0.0
    for column, weight in (("sma_20", 0.45), ("sma_60", 0.35), ("ema_20", 0.20)):
        value = _safe_number(latest.get(column, np.nan))
        if value and close > value:
            score += weight
        elif value and close < value:
            score -= weight
    return score


def _trend_label(score: float) -> str:
    if score >= 0.55:
        return "bullish"
    if score <= -0.55:
        return "bearish"
    return "neutral"


def _rsi_score(value: float) -> float:
    if 45 <= value <= 60:
        return 6.0
    if 35 <= value < 45 or 60 < value <= 70:
        return 2.0
    if value < 25 or value > 80:
        return -8.0
    return -2.0


def _safe_number(value: object, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(number):
        return default
    return number

