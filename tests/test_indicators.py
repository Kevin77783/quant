import numpy as np

from quant_system.analysis import add_indicators, analyze_prices
from quant_system.data import CSVDataProvider


def test_add_indicators_produces_expected_columns() -> None:
    prices = CSVDataProvider("data/sample_prices.csv").get_history("000001.SZ", "cn")

    enriched = add_indicators(prices, ma_windows=(5, 20))

    assert {"sma_5", "sma_20", "rsi", "macd_hist", "atr", "drawdown"}.issubset(enriched.columns)
    assert np.isfinite(enriched.iloc[-1]["rsi"])
    assert enriched.iloc[-1]["sma_5"] > 0


def test_analyze_prices_returns_actionable_report() -> None:
    prices = CSVDataProvider("data/sample_prices.csv").get_history("0700.HK", "hk")

    report = analyze_prices(prices)

    assert report["symbol"] == "0700.HK"
    assert report["market"] == "hk"
    assert 0 <= report["score"] <= 100
    assert report["trend"] in {"bullish", "neutral", "bearish"}
    assert "sharpe" in report["performance"]

