from __future__ import annotations

import pandas as pd
import streamlit as st

from quant_system.analysis import analyze_prices, screen_universe
from quant_system.backtest import BacktestConfig, BacktestEngine, PortfolioBacktestConfig, PortfolioBacktestEngine
from quant_system.config import load_yaml, parse_universe
from quant_system.data import AutoDataProvider, CSVDataProvider
from quant_system.strategies import build_strategy


st.set_page_config(page_title="Quant System", layout="wide")
st.title("Multi-Market Quant System")

mode = st.sidebar.radio("Mode", ["Single Stock", "Universe Screen", "Portfolio Backtest"])
provider_name = st.sidebar.selectbox("Provider", ["csv", "auto"], index=0)
data_file = st.sidebar.text_input("CSV data file", "data/sample_prices.csv")
config_file = st.sidebar.text_input("Config file", "configs/default.yaml")


def provider():
    if provider_name == "auto":
        return AutoDataProvider(data_file, cache_dir="data", use_cache=True)
    return CSVDataProvider(data_file)


if mode == "Single Stock":
    col1, col2 = st.columns(2)
    symbol = col1.text_input("Symbol", "AAPL")
    market = col2.selectbox("Market", ["cn", "hk", "us"], index=2)
    strategy_name = st.selectbox("Strategy", ["ma", "rsi", "breakout"], index=0)
    if st.button("Analyze"):
        prices = provider().get_history(symbol, market)
        report = analyze_prices(prices)
        st.metric("Close", f"{report['close']:.4f}")
        st.metric("Score", f"{report['score']:.2f}/100")
        st.metric("Trend", str(report["trend"]))
        st.subheader("Signals")
        st.dataframe(pd.DataFrame([report["signals"]]).T.rename(columns={0: "value"}), use_container_width=True)
        st.subheader("Buy and Hold Performance")
        st.dataframe(pd.DataFrame([report["performance"]]).T.rename(columns={0: "value"}), use_container_width=True)

        strategy = build_strategy(strategy_name, short_window=5, long_window=20)
        result = BacktestEngine(BacktestConfig()).run(prices, strategy)
        st.subheader("Backtest Equity")
        st.line_chart(result.equity_curve.set_index("date")[["equity", "benchmark_equity"]])
        st.dataframe(pd.DataFrame([result.metrics]).T.rename(columns={0: "value"}), use_container_width=True)

elif mode == "Universe Screen":
    top = st.sidebar.number_input("Top N", min_value=1, value=10)
    if st.button("Run Screen"):
        universe = parse_universe(load_yaml(config_file))
        ranked = screen_universe(universe, provider(), top=int(top))
        st.dataframe(ranked.drop(columns=["turnover_proxy"], errors="ignore"), use_container_width=True)

else:
    top_n = st.sidebar.number_input("Hold Top N", min_value=1, value=3)
    rebalance = st.sidebar.number_input("Rebalance Frequency", min_value=1, value=5)
    weighting = st.sidebar.selectbox("Weighting", ["equal", "inverse_vol"])
    if st.button("Run Portfolio Backtest"):
        universe = parse_universe(load_yaml(config_file))
        engine = PortfolioBacktestEngine(
            PortfolioBacktestConfig(top_n=int(top_n), rebalance_frequency=int(rebalance), weighting=weighting)
        )
        result = engine.run(universe, provider())
        st.line_chart(result.equity_curve.set_index("date")[["equity", "benchmark_equity"]])
        st.dataframe(pd.DataFrame([result.metrics]).T.rename(columns={0: "value"}), use_container_width=True)
        st.subheader("Weights")
        st.dataframe(result.weights, use_container_width=True)

