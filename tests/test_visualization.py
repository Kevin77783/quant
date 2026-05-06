import pandas as pd

from quant_system.data import CSVDataProvider
from quant_system.timeframe import resample_ohlcv
from quant_system.visualization import (
    make_alerts_bar,
    make_candlestick_figure,
    make_correlation_heatmap,
    make_factor_bar,
    make_normalized_performance_figure,
    make_optimization_heatmap,
    make_risk_return_scatter,
    make_screen_scatter,
)
from quant_system.analysis import analyze_prices


def test_resample_ohlcv_to_weekly_bars() -> None:
    prices = CSVDataProvider("data/sample_prices.csv").get_history("AAPL", "us")

    weekly = resample_ohlcv(prices, "weekly")

    assert len(weekly) < len(prices)
    assert {"open", "high", "low", "close", "volume"}.issubset(weekly.columns)
    assert weekly["symbol"].iloc[-1] == "AAPL"


def test_candlestick_figure_contains_kline_and_indicator_traces() -> None:
    prices = CSVDataProvider("data/sample_prices.csv").get_history("AAPL", "us")

    figure = make_candlestick_figure(prices)

    trace_types = {trace.type for trace in figure.data}
    assert "candlestick" in trace_types
    assert "bar" in trace_types
    assert "scatter" in trace_types


def test_factor_bar_uses_analysis_signals() -> None:
    prices = CSVDataProvider("data/sample_prices.csv").get_history("AAPL", "us")
    report = analyze_prices(prices)

    figure = make_factor_bar(report["signals"])

    assert len(figure.data) == 1
    assert figure.data[0].type == "bar"


def test_screen_scatter_handles_empty_filter_result() -> None:
    figure = make_screen_scatter(
        pd.DataFrame(
            columns=["volatility_20", "score", "symbol", "liquidity_score", "momentum_20_pct", "market", "trend", "rsi"]
        )
    )

    assert len(figure.layout.annotations) == 1


def test_comparison_figures_use_expected_trace_types() -> None:
    normalized = pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=2),
            "AAPL": [100.0, 103.0],
            "0700.HK": [100.0, 98.0],
        }
    )
    summary = pd.DataFrame(
        {
            "symbol": ["AAPL", "0700.HK"],
            "market": ["us", "hk"],
            "total_return": [0.03, -0.02],
            "annual_volatility": [0.2, 0.3],
            "sharpe": [1.2, -0.4],
            "max_drawdown": [-0.01, -0.04],
            "win_rate": [0.6, 0.4],
        }
    )
    correlation = pd.DataFrame([[1.0, 0.2], [0.2, 1.0]], index=["AAPL", "0700.HK"], columns=["AAPL", "0700.HK"])

    performance = make_normalized_performance_figure(normalized)
    scatter = make_risk_return_scatter(summary)
    heatmap = make_correlation_heatmap(correlation)

    assert {trace.type for trace in performance.data} == {"scatter"}
    assert scatter.data[0].type == "scatter"
    assert heatmap.data[0].type == "heatmap"


def test_optimization_and_alert_figures_render_core_traces() -> None:
    optimization = pd.DataFrame(
        {
            "short_window": [3, 5],
            "long_window": [20, 20],
            "sharpe": [1.0, 0.7],
        }
    )
    alerts = pd.DataFrame(
        {
            "symbol": ["AAPL", "0700.HK"],
            "trigger_count": [2, 1],
            "score": [84.0, 76.0],
            "alerts": ["score>=80; rsi_overbought>=75", "weak_momentum<=-5%"],
        }
    )

    optimization_figure = make_optimization_heatmap(optimization, metric="sharpe")
    alerts_figure = make_alerts_bar(alerts)

    assert optimization_figure.data[0].type == "heatmap"
    assert alerts_figure.data[0].type == "bar"
