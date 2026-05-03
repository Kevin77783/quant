from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from quant_system.analysis.performance import calculate_performance
from quant_system.models import normalize_ohlcv
from quant_system.strategies import Strategy


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 100000.0
    commission_bps: float = 2.0
    slippage_bps: float = 1.0
    risk_free_rate: float = 0.0


@dataclass
class BacktestResult:
    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    signals: pd.DataFrame
    metrics: dict[str, float]
    strategy_name: str

    def save(self, output_dir: str | Path) -> None:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        self.equity_curve.to_csv(path / "equity_curve.csv", index=False)
        self.trades.to_csv(path / "trades.csv", index=False)
        self.signals.to_csv(path / "signals.csv", index=False)
        pd.DataFrame([self.metrics]).to_csv(path / "metrics.csv", index=False)


class BacktestEngine:
    """Daily vectorized long-only backtest with next-bar execution."""

    def __init__(self, config: BacktestConfig | None = None):
        self.config = config or BacktestConfig()

    def run(self, prices: pd.DataFrame, strategy: Strategy) -> BacktestResult:
        data = normalize_ohlcv(prices)
        signals = strategy.generate_signals(data)
        aligned = data[["date", "symbol", "market", "close"]].join(
            signals[["target_weight", "reason"]], how="left"
        )
        aligned["target_weight"] = aligned["target_weight"].fillna(0.0).clip(0.0, 1.0)

        aligned["asset_return"] = aligned["close"].pct_change().fillna(0.0)
        aligned["position"] = aligned["target_weight"].shift(1).fillna(0.0)
        aligned["turnover"] = aligned["position"].diff().abs().fillna(aligned["position"].abs())
        cost_rate = (self.config.commission_bps + self.config.slippage_bps) / 10000.0
        aligned["cost"] = aligned["turnover"] * cost_rate
        aligned["strategy_return"] = aligned["position"] * aligned["asset_return"] - aligned["cost"]
        aligned["equity"] = self.config.initial_cash * (1.0 + aligned["strategy_return"]).cumprod()
        aligned["benchmark_equity"] = self.config.initial_cash * (1.0 + aligned["asset_return"]).cumprod()
        aligned["drawdown"] = aligned["equity"] / aligned["equity"].cummax() - 1.0

        metrics = calculate_performance(aligned["equity"], risk_free_rate=self.config.risk_free_rate)
        benchmark_metrics = calculate_performance(
            aligned["benchmark_equity"],
            risk_free_rate=self.config.risk_free_rate,
        )
        for key, value in benchmark_metrics.items():
            metrics[f"benchmark_{key}"] = value
        metrics["excess_total_return"] = metrics["total_return"] - metrics["benchmark_total_return"]

        equity_curve = aligned[
            [
                "date",
                "symbol",
                "market",
                "close",
                "asset_return",
                "position",
                "turnover",
                "cost",
                "strategy_return",
                "equity",
                "benchmark_equity",
                "drawdown",
            ]
        ].reset_index(drop=True)
        trades = _extract_trades(aligned)
        return BacktestResult(
            equity_curve=equity_curve,
            trades=trades,
            signals=signals.reset_index(drop=True),
            metrics=metrics,
            strategy_name=strategy.name,
        )


def _extract_trades(aligned: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    previous_position = 0.0
    for _, row in aligned.iterrows():
        position = float(row["position"])
        if abs(position - previous_position) > 1e-12:
            rows.append(
                {
                    "date": row["date"],
                    "symbol": row.get("symbol", ""),
                    "market": row.get("market", ""),
                    "action": "BUY" if position > previous_position else "SELL",
                    "price": row["close"],
                    "previous_weight": previous_position,
                    "new_weight": position,
                    "turnover": abs(position - previous_position),
                    "reason": row.get("reason", ""),
                }
            )
        previous_position = position
    return pd.DataFrame(rows)

