from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from quant_system.analysis.factors import factor_frame
from quant_system.analysis.indicators import add_indicators
from quant_system.analysis.performance import calculate_performance
from quant_system.backtest.engine import BacktestConfig
from quant_system.data.providers import DataProvider
from quant_system.models import Security


@dataclass(frozen=True)
class PortfolioBacktestConfig(BacktestConfig):
    top_n: int = 5
    rebalance_frequency: int = 20
    weighting: str = "equal"


@dataclass
class PortfolioBacktestResult:
    equity_curve: pd.DataFrame
    weights: pd.DataFrame
    rebalance_log: pd.DataFrame
    metrics: dict[str, float]

    def save(self, output_dir: str | Path) -> None:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        self.equity_curve.to_csv(path / "portfolio_equity_curve.csv", index=False)
        self.weights.to_csv(path / "portfolio_weights.csv", index=False)
        self.rebalance_log.to_csv(path / "portfolio_rebalance_log.csv", index=False)
        pd.DataFrame([self.metrics]).to_csv(path / "portfolio_metrics.csv", index=False)


class PortfolioBacktestEngine:
    """Multi-asset long-only factor portfolio backtest with periodic rebalancing."""

    def __init__(self, config: PortfolioBacktestConfig | None = None):
        self.config = config or PortfolioBacktestConfig()

    def run(
        self,
        universe: list[Security],
        provider: DataProvider,
        start: str | None = None,
        end: str | None = None,
    ) -> PortfolioBacktestResult:
        if not universe:
            raise ValueError("Portfolio universe is empty.")
        if self.config.top_n < 1:
            raise ValueError("top_n must be at least 1.")
        if self.config.rebalance_frequency < 1:
            raise ValueError("rebalance_frequency must be at least 1.")

        closes: dict[str, pd.Series] = {}
        factors: dict[str, pd.DataFrame] = {}
        failures: list[str] = []

        for security in universe:
            key = security.symbol
            try:
                prices = provider.get_history(security.symbol, security.market, start=start, end=end)
                enriched = add_indicators(prices)
                closes[key] = enriched["close"].rename(key)
                factors[key] = factor_frame(enriched)
            except Exception as exc:
                failures.append(f"{security.symbol}({security.market.value}): {exc}")

        if not closes:
            raise RuntimeError("No securities could be loaded for portfolio backtest:\n" + "\n".join(failures))

        close_frame = pd.concat(closes.values(), axis=1).sort_index().ffill()
        returns = close_frame.pct_change().fillna(0.0)
        weights = pd.DataFrame(np.nan, index=close_frame.index, columns=close_frame.columns)
        rebalance_rows: list[dict[str, object]] = []

        for offset, date in enumerate(close_frame.index):
            if offset % self.config.rebalance_frequency != 0:
                continue
            scores = self._scores_on_date(factors, date)
            if scores.empty:
                continue
            selected = scores.sort_values("composite_score", ascending=False).head(self.config.top_n)
            row_weights = self._weights_for_selection(selected)
            weights.loc[date, :] = 0.0
            weights.loc[date, row_weights.index] = row_weights
            rebalance_rows.append(
                {
                    "date": date,
                    "selected": ",".join(row_weights.index),
                    "avg_score": float(selected["composite_score"].mean()),
                    "weighting": self.config.weighting,
                }
            )

        weights = weights.ffill().fillna(0.0)
        execution_weights = weights.shift(1).fillna(0.0)
        gross_return = (execution_weights * returns).sum(axis=1)
        turnover = execution_weights.diff().abs().sum(axis=1).fillna(execution_weights.abs().sum(axis=1))
        cost_rate = (self.config.commission_bps + self.config.slippage_bps) / 10000.0
        strategy_return = gross_return - turnover * cost_rate
        equity = self.config.initial_cash * (1.0 + strategy_return).cumprod()

        equal_weight_benchmark = returns.mean(axis=1)
        benchmark_equity = self.config.initial_cash * (1.0 + equal_weight_benchmark).cumprod()
        metrics = calculate_performance(equity, risk_free_rate=self.config.risk_free_rate)
        benchmark_metrics = calculate_performance(benchmark_equity, risk_free_rate=self.config.risk_free_rate)
        for key, value in benchmark_metrics.items():
            metrics[f"benchmark_{key}"] = value
        metrics["excess_total_return"] = metrics["total_return"] - metrics["benchmark_total_return"]
        metrics["avg_turnover"] = float(turnover.mean())
        metrics["rebalance_count"] = float(len(rebalance_rows))
        metrics["loaded_symbols"] = float(len(closes))
        metrics["failed_symbols"] = float(len(failures))

        equity_curve = pd.DataFrame(
            {
                "date": close_frame.index,
                "portfolio_return": strategy_return.values,
                "gross_return": gross_return.values,
                "turnover": turnover.values,
                "cost": (turnover * cost_rate).values,
                "equity": equity.values,
                "benchmark_equity": benchmark_equity.values,
                "drawdown": (equity / equity.cummax() - 1.0).values,
            }
        )
        weights_out = weights.copy()
        weights_out.insert(0, "date", weights.index)
        rebalance_log = pd.DataFrame(rebalance_rows)
        if failures:
            rebalance_log.attrs["failures"] = failures
        return PortfolioBacktestResult(
            equity_curve=equity_curve,
            weights=weights_out.reset_index(drop=True),
            rebalance_log=rebalance_log,
            metrics=metrics,
        )

    def _scores_on_date(self, factors: dict[str, pd.DataFrame], date: pd.Timestamp) -> pd.DataFrame:
        rows: list[pd.Series] = []
        for symbol, frame in factors.items():
            available = frame.loc[frame.index <= date]
            if available.empty:
                continue
            row = available.iloc[-1].copy()
            row["symbol"] = symbol
            rows.append(row)
        return pd.DataFrame(rows)

    def _weights_for_selection(self, selected: pd.DataFrame) -> pd.Series:
        symbols = selected["symbol"].astype(str)
        if self.config.weighting == "inverse_vol":
            vol = selected["volatility_20"].replace(0, np.nan).astype(float)
            raw = (1.0 / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0)
            if raw.sum() > 0:
                return pd.Series(raw.values / raw.sum(), index=symbols.values)
        if self.config.weighting != "equal":
            raise ValueError("weighting must be 'equal' or 'inverse_vol'.")
        return pd.Series(1.0 / len(selected), index=symbols.values)
