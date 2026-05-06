from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from quant_system.backtest.engine import BacktestConfig, BacktestEngine
from quant_system.strategies import MovingAverageCrossStrategy


def optimize_ma_strategy(
    prices: pd.DataFrame,
    short_windows: Iterable[int] = (3, 5, 10),
    long_windows: Iterable[int] = (20, 40, 60),
    config: BacktestConfig | None = None,
    rank_metric: str = "sharpe",
) -> pd.DataFrame:
    """Grid-search moving-average crossover parameters."""

    engine = BacktestEngine(config or BacktestConfig())
    rows: list[dict[str, float | int]] = []
    for short_window in sorted(set(int(value) for value in short_windows)):
        for long_window in sorted(set(int(value) for value in long_windows)):
            if short_window >= long_window:
                continue
            strategy = MovingAverageCrossStrategy(short_window=short_window, long_window=long_window)
            result = engine.run(prices, strategy)
            rows.append(
                {
                    "short_window": short_window,
                    "long_window": long_window,
                    "total_return": result.metrics["total_return"],
                    "annual_return": result.metrics["annual_return"],
                    "annual_volatility": result.metrics["annual_volatility"],
                    "sharpe": result.metrics["sharpe"],
                    "max_drawdown": result.metrics["max_drawdown"],
                    "win_rate": result.metrics["win_rate"],
                    "excess_total_return": result.metrics["excess_total_return"],
                    "trades": len(result.trades),
                }
            )
    if not rows:
        raise ValueError("No valid moving-average parameter pairs were generated.")
    table = pd.DataFrame(rows)
    if rank_metric not in table.columns:
        raise ValueError(f"rank_metric must be one of: {', '.join(table.columns)}")
    return table.sort_values(rank_metric, ascending=False).reset_index(drop=True)

