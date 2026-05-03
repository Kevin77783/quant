from __future__ import annotations

import math

import numpy as np
import pandas as pd


def calculate_performance(
    equity: pd.Series | pd.DataFrame,
    periods_per_year: int = 252,
    risk_free_rate: float = 0.0,
) -> dict[str, float]:
    """Calculate standard performance metrics from an equity curve."""

    curve = _extract_equity_series(equity).dropna().astype(float)
    if len(curve) < 2:
        return {
            "total_return": 0.0,
            "annual_return": 0.0,
            "annual_volatility": 0.0,
            "sharpe": 0.0,
            "max_drawdown": 0.0,
            "calmar": 0.0,
            "win_rate": 0.0,
            "best_day": 0.0,
            "worst_day": 0.0,
        }

    returns = curve.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    total_return = curve.iloc[-1] / curve.iloc[0] - 1.0
    years = max(len(returns) / periods_per_year, 1 / periods_per_year)
    annual_return = (1.0 + total_return) ** (1.0 / years) - 1.0 if total_return > -1 else -1.0
    annual_volatility = returns.std(ddof=0) * math.sqrt(periods_per_year) if len(returns) else 0.0
    annual_excess_return = returns.mean() * periods_per_year - risk_free_rate if len(returns) else 0.0
    sharpe = annual_excess_return / annual_volatility if annual_volatility > 0 else 0.0
    drawdown = drawdown_series(curve)
    max_drawdown = drawdown.min() if not drawdown.empty else 0.0
    calmar = annual_return / abs(max_drawdown) if max_drawdown < 0 else 0.0

    return {
        "total_return": float(total_return),
        "annual_return": float(annual_return),
        "annual_volatility": float(annual_volatility),
        "sharpe": float(sharpe),
        "max_drawdown": float(max_drawdown),
        "calmar": float(calmar),
        "win_rate": float((returns > 0).mean()) if len(returns) else 0.0,
        "best_day": float(returns.max()) if len(returns) else 0.0,
        "worst_day": float(returns.min()) if len(returns) else 0.0,
    }


def drawdown_series(equity: pd.Series | pd.DataFrame) -> pd.Series:
    curve = _extract_equity_series(equity).dropna().astype(float)
    return curve / curve.cummax() - 1.0


def _extract_equity_series(equity: pd.Series | pd.DataFrame) -> pd.Series:
    if isinstance(equity, pd.Series):
        return equity
    if "equity" in equity.columns:
        return equity["equity"]
    if equity.shape[1] == 1:
        return equity.iloc[:, 0]
    raise ValueError("Equity DataFrame must contain an 'equity' column.")

