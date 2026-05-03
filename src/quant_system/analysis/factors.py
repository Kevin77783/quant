from __future__ import annotations

import numpy as np
import pandas as pd


def factor_snapshot(enriched_prices: pd.DataFrame) -> dict[str, float]:
    """Return a multi-factor snapshot for the latest row of an indicator frame."""

    return factor_row(enriched_prices.iloc[-1])


def factor_frame(enriched_prices: pd.DataFrame) -> pd.DataFrame:
    """Return per-date factor scores for an indicator frame."""

    rows = [factor_row(row) for _, row in enriched_prices.iterrows()]
    factors = pd.DataFrame(rows, index=enriched_prices.index)
    factors["date"] = enriched_prices["date"].values
    factors["symbol"] = enriched_prices["symbol"].values if "symbol" in enriched_prices.columns else ""
    factors["market"] = enriched_prices["market"].values if "market" in enriched_prices.columns else ""
    return factors


def factor_row(row: pd.Series) -> dict[str, float]:
    close = _safe_number(row.get("close", np.nan))
    turnover = _safe_number(row.get("close", 0.0)) * _safe_number(row.get("volume", 0.0))
    trend_score = _trend_score(row)
    momentum_20 = _safe_number(row.get("momentum_20", 0.0))
    momentum_60 = _safe_number(row.get("momentum_60", 0.0))
    volatility_20 = _safe_number(row.get("volatility_20", 0.35))
    volatility_60 = _safe_number(row.get("volatility_60", volatility_20))
    drawdown = _safe_number(row.get("drawdown", 0.0))
    rsi_value = _safe_number(row.get("rsi", 50.0))
    macd_hist = _safe_number(row.get("macd_hist", 0.0))
    atr = _safe_number(row.get("atr", 0.0))
    atr_pct = atr / close if close > 0 else 0.0

    return {
        "trend_score": trend_score,
        "momentum_20_pct": momentum_20 * 100.0,
        "momentum_60_pct": momentum_60 * 100.0,
        "volatility_20": volatility_20,
        "volatility_60": volatility_60,
        "liquidity_score": liquidity_score(turnover),
        "turnover_proxy": turnover,
        "rsi": rsi_value,
        "rsi_balance_score": rsi_balance_score(rsi_value),
        "macd_hist": macd_hist,
        "drawdown": drawdown,
        "atr_pct": atr_pct,
        "composite_score": composite_score(
            trend_score=trend_score,
            momentum_20=momentum_20,
            momentum_60=momentum_60,
            volatility_20=volatility_20,
            liquidity=liquidity_score(turnover),
            rsi_balance=rsi_balance_score(rsi_value),
            macd_hist=macd_hist,
            drawdown=drawdown,
        ),
    }


def composite_score(
    trend_score: float,
    momentum_20: float,
    momentum_60: float,
    volatility_20: float,
    liquidity: float,
    rsi_balance: float,
    macd_hist: float,
    drawdown: float,
) -> float:
    score = 50.0
    score += trend_score * 14.0
    score += np.clip(momentum_20 * 100.0, -16, 16)
    score += np.clip(momentum_60 * 55.0, -10, 10)
    score += np.clip((0.35 - volatility_20) * 24.0, -10, 10)
    score += liquidity * 4.0
    score += rsi_balance * 8.0
    score += np.clip(macd_hist * 3.0, -5, 5)
    score += np.clip(drawdown * 40.0, -12, 0)
    return float(np.clip(score, 0, 100))


def liquidity_score(turnover_proxy: float) -> float:
    if turnover_proxy <= 0:
        return -1.0
    return float(np.clip((np.log10(turnover_proxy) - 7.0) / 3.0, -1.0, 1.0))


def rsi_balance_score(value: float) -> float:
    if 45 <= value <= 60:
        return 1.0
    if 35 <= value < 45 or 60 < value <= 70:
        return 0.35
    if value < 25 or value > 80:
        return -1.0
    return -0.35


def _trend_score(latest: pd.Series) -> float:
    close = _safe_number(latest.get("close", np.nan))
    score = 0.0
    for column, weight in (("sma_20", 0.45), ("sma_60", 0.35), ("ema_20", 0.20)):
        value = _safe_number(latest.get(column, np.nan))
        if value and close > value:
            score += weight
        elif value and close < value:
            score -= weight
    return float(score)


def _safe_number(value: object, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if not np.isfinite(number):
        return default
    return number
