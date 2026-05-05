import pandas as pd

from quant_system.data import CSVDataProvider
from quant_system.timeframe import resample_ohlcv
from quant_system.visualization import make_candlestick_figure, make_factor_bar, make_screen_scatter
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
