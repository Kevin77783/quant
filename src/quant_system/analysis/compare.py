from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from quant_system.analysis.performance import calculate_performance, drawdown_series
from quant_system.data.providers import DataProvider
from quant_system.models import Security


@dataclass
class ComparisonResult:
    normalized: pd.DataFrame
    summary: pd.DataFrame
    correlation: pd.DataFrame
    failures: list[str]


def compare_universe(
    universe: list[Security],
    provider: DataProvider,
    start: str | None = None,
    end: str | None = None,
    base: float = 100.0,
) -> ComparisonResult:
    """Compare normalized price performance, risk, and correlations across securities."""

    closes: dict[str, pd.Series] = {}
    meta: dict[str, Security] = {}
    failures: list[str] = []
    for security in universe:
        try:
            prices = provider.get_history(security.symbol, security.market, start=start, end=end)
            closes[security.symbol] = prices["close"].rename(security.symbol)
            meta[security.symbol] = security
        except Exception as exc:
            failures.append(f"{security.symbol}({security.market.value}): {exc}")

    if not closes:
        raise RuntimeError("No securities could be compared:\n" + "\n".join(failures))

    close_frame = pd.concat(closes.values(), axis=1).sort_index().ffill().dropna(how="all")
    normalized = close_frame.divide(close_frame.bfill().iloc[0]).multiply(base)
    returns = close_frame.pct_change().dropna(how="all")
    rows: list[dict[str, object]] = []
    for symbol in close_frame.columns:
        series = close_frame[symbol].dropna()
        if len(series) < 2:
            continue
        equity = series / series.iloc[0]
        metrics = calculate_performance(equity)
        security = meta[symbol]
        rows.append(
            {
                "symbol": symbol,
                "market": security.market.value,
                "name": security.name or "",
                "latest_close": float(series.iloc[-1]),
                "total_return": metrics["total_return"],
                "annual_return": metrics["annual_return"],
                "annual_volatility": metrics["annual_volatility"],
                "sharpe": metrics["sharpe"],
                "max_drawdown": metrics["max_drawdown"],
                "win_rate": metrics["win_rate"],
                "current_drawdown": float(drawdown_series(series).iloc[-1]),
            }
        )
    if not rows:
        raise RuntimeError("Compared securities did not contain enough price history.")
    summary = pd.DataFrame(rows).sort_values("total_return", ascending=False).reset_index(drop=True)
    correlation = returns.corr().fillna(0.0)
    normalized = normalized.reset_index().rename(columns={close_frame.index.name or "index": "date"})
    return ComparisonResult(normalized=normalized, summary=summary, correlation=correlation, failures=failures)
