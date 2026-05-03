from __future__ import annotations

import numpy as np
import pandas as pd

from quant_system.analysis.factors import factor_snapshot
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

    factors = factor_snapshot(data)
    trend_score = factors["trend_score"]
    factor_score = factors["composite_score"]

    return {
        "symbol": str(latest.get("symbol", "")),
        "market": str(latest.get("market", "")),
        "date": latest["date"].date().isoformat(),
        "close": float(latest["close"]),
        "trend": _trend_label(trend_score),
        "score": round(float(factor_score), 2),
        "signals": {
            "trend_score": round(float(trend_score), 2),
            "momentum_20_pct": round(float(factors["momentum_20_pct"]), 2),
            "momentum_60_pct": round(float(factors["momentum_60_pct"]), 2),
            "volatility_20": round(float(factors["volatility_20"]), 4),
            "volatility_60": round(float(factors["volatility_60"]), 4),
            "liquidity_score": round(float(factors["liquidity_score"]), 4),
            "rsi": round(float(factors["rsi"]), 2),
            "rsi_balance_score": round(float(factors["rsi_balance_score"]), 4),
            "macd_hist": round(float(factors["macd_hist"]), 4),
            "atr_pct": round(float(factors["atr_pct"]), 4),
            "drawdown": round(float(factors["drawdown"]), 4),
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
    failures: list[str] = []
    for security in universe:
        try:
            prices = provider.get_history(security.symbol, security.market, start=start, end=end)
            enriched = add_indicators(prices)
            latest = enriched.iloc[-1]
            report = analyze_prices(prices)
            factors = factor_snapshot(enriched)
        except Exception as exc:
            failures.append(f"{security.symbol}({security.market.value}): {exc}")
            continue
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
                "momentum_60_pct": report["signals"]["momentum_60_pct"],
                "volatility_20": report["signals"]["volatility_20"],
                "liquidity_score": report["signals"]["liquidity_score"],
                "drawdown": report["signals"]["drawdown"],
                "atr_pct": report["signals"]["atr_pct"],
                "turnover_proxy": float(factors["turnover_proxy"]),
            }
        )

    if not rows:
        joined = "\n".join(failures)
        raise RuntimeError(f"No securities could be screened. Failures:\n{joined}")

    ranked = pd.DataFrame(rows).sort_values(["score", "turnover_proxy"], ascending=[False, False])
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    if top is not None:
        ranked = ranked.head(top)
    result = ranked.reset_index(drop=True)
    if failures:
        result.attrs["failures"] = failures
    return result


def _trend_label(score: float) -> str:
    if score >= 0.55:
        return "bullish"
    if score <= -0.55:
        return "bearish"
    return "neutral"
