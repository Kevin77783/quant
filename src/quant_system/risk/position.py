from __future__ import annotations

import numpy as np
import pandas as pd


def fixed_fraction_position(
    cash: float,
    price: float,
    risk_fraction: float = 0.02,
    stop_loss_pct: float = 0.08,
    lot_size: int = 1,
) -> int:
    """Position size from fixed capital-at-risk and stop distance."""

    if price <= 0:
        raise ValueError("price must be positive.")
    if not (0 < risk_fraction <= 1):
        raise ValueError("risk_fraction must be in (0, 1].")
    if not (0 < stop_loss_pct < 1):
        raise ValueError("stop_loss_pct must be in (0, 1).")
    raw_shares = cash * risk_fraction / (price * stop_loss_pct)
    shares = int(raw_shares // lot_size * lot_size)
    return max(shares, 0)


def volatility_target_weight(
    returns: pd.Series,
    target_volatility: float = 0.15,
    max_weight: float = 1.0,
    lookback: int = 20,
) -> pd.Series:
    """Scale exposure so realized annualized volatility approaches a target."""

    realized = returns.rolling(lookback, min_periods=max(2, lookback // 2)).std() * np.sqrt(252)
    weights = target_volatility / realized.replace(0, np.nan)
    return weights.replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(0.0, max_weight)


def kelly_fraction(win_rate: float, win_loss_ratio: float, cap: float = 0.25) -> float:
    """Conservative capped Kelly fraction."""

    if not (0 <= win_rate <= 1):
        raise ValueError("win_rate must be in [0, 1].")
    if win_loss_ratio <= 0:
        raise ValueError("win_loss_ratio must be positive.")
    raw = win_rate - (1 - win_rate) / win_loss_ratio
    return float(np.clip(raw, 0.0, cap))


def apply_drawdown_kill_switch(
    equity: pd.Series,
    target_weight: pd.Series,
    max_drawdown: float = -0.15,
) -> pd.Series:
    """Set target exposure to zero after equity drawdown breaches a threshold."""

    if max_drawdown >= 0:
        raise ValueError("max_drawdown should be negative, for example -0.15.")
    drawdown = equity / equity.cummax() - 1.0
    killed = drawdown <= max_drawdown
    if not killed.any():
        return target_weight.copy()
    first_kill = killed.idxmax()
    adjusted = target_weight.copy()
    adjusted.loc[first_kill:] = 0.0
    return adjusted

