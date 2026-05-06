from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quant_system.analysis.report import analyze_prices
from quant_system.data.providers import DataProvider
from quant_system.models import Security


@dataclass(frozen=True)
class AlertRule:
    min_score: float = 80.0
    max_rsi: float = 75.0
    min_rsi: float = 30.0
    max_drawdown: float = -0.10
    min_momentum_20_pct: float = -5.0
    include_bearish: bool = True
    include_all: bool = False


def scan_alerts(
    universe: list[Security],
    provider: DataProvider,
    rule: AlertRule | None = None,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Scan a universe for simple research alerts."""

    active_rule = rule or AlertRule()
    rows: list[dict[str, object]] = []
    failures: list[str] = []
    for security in universe:
        try:
            prices = provider.get_history(security.symbol, security.market, start=start, end=end)
            report = analyze_prices(prices)
            alerts = _alerts_for_report(report, active_rule)
        except Exception as exc:
            failures.append(f"{security.symbol}({security.market.value}): {exc}")
            continue
        if alerts or active_rule.include_all:
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
                    "drawdown": report["signals"]["drawdown"],
                    "trigger_count": len(alerts),
                    "alerts": "; ".join(alerts) if alerts else "none",
                }
            )

    if not rows:
        result = pd.DataFrame(
            columns=[
                "symbol",
                "market",
                "name",
                "date",
                "close",
                "score",
                "trend",
                "rsi",
                "momentum_20_pct",
                "drawdown",
                "trigger_count",
                "alerts",
            ]
        )
    else:
        result = pd.DataFrame(rows).sort_values(["trigger_count", "score"], ascending=[False, False]).reset_index(drop=True)
    if failures:
        result.attrs["failures"] = failures
    return result


def _alerts_for_report(report: dict[str, object], rule: AlertRule) -> list[str]:
    signals = report["signals"]
    alerts: list[str] = []
    if float(report["score"]) >= rule.min_score:
        alerts.append(f"score>={rule.min_score:g}")
    if float(signals["rsi"]) >= rule.max_rsi:
        alerts.append(f"rsi_overbought>={rule.max_rsi:g}")
    if float(signals["rsi"]) <= rule.min_rsi:
        alerts.append(f"rsi_oversold<={rule.min_rsi:g}")
    if float(signals["drawdown"]) <= rule.max_drawdown:
        alerts.append(f"drawdown<={rule.max_drawdown:.0%}")
    if float(signals["momentum_20_pct"]) <= rule.min_momentum_20_pct:
        alerts.append(f"weak_momentum<={rule.min_momentum_20_pct:g}%")
    if rule.include_bearish and str(report["trend"]) == "bearish":
        alerts.append("bearish_trend")
    return alerts

