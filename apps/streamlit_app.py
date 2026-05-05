from __future__ import annotations

import pandas as pd
import streamlit as st

from quant_system.analysis import add_indicators, analyze_prices, screen_universe
from quant_system.backtest import BacktestConfig, BacktestEngine, PortfolioBacktestConfig, PortfolioBacktestEngine
from quant_system.config import load_yaml, parse_universe
from quant_system.risk import fixed_fraction_position
from quant_system.strategies import build_strategy
from quant_system.timeframe import resample_ohlcv
from quant_system.visualization import (
    make_candlestick_figure,
    make_equity_drawdown_figure,
    make_factor_bar,
    make_score_gauge,
    make_screen_scatter,
    make_weights_figure,
)
from quant_system.workflows import ProviderSettings, build_data_provider


MARKET_DEFAULTS = {
    "cn": "000001.SZ",
    "hk": "0700.HK",
    "us": "AAPL",
}

MARKET_LABELS = {
    "cn": "A Share",
    "hk": "Hong Kong",
    "us": "United States",
}


st.set_page_config(page_title="Quant Workbench", layout="wide", initial_sidebar_state="expanded")
st.markdown(
    """
    <style>
      .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1480px; }
      [data-testid="stSidebar"] { background: #f8fafc; border-right: 1px solid #e2e8f0; }
      div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 14px;
      }
      .section-title { font-size: 1.05rem; font-weight: 700; margin: 0.3rem 0 0.7rem; }
      .small-note { color: #64748b; font-size: 0.85rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_prices(
    provider_name: str,
    data_file: str,
    cache_dir: str,
    use_cache: bool,
    symbol: str,
    market: str,
    start: str | None,
    end: str | None,
    adjust: str,
    interval: str,
) -> pd.DataFrame:
    provider = build_data_provider(
        ProviderSettings(provider=provider_name, data_file=data_file, cache_dir=cache_dir, use_cache=use_cache)
    )
    return provider.get_history(symbol, market, start=start, end=end, adjust=adjust, interval=interval)


def build_provider(provider_name: str, data_file: str, cache_dir: str, use_cache: bool):
    return build_data_provider(
        ProviderSettings(provider=provider_name, data_file=data_file, cache_dir=cache_dir, use_cache=use_cache)
    )


def fmt_pct(value: float) -> str:
    return f"{value:.2%}"


def metrics_frame(metrics: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"metric": key, "value": value} for key, value in metrics.items()]
    )


with st.sidebar:
    st.title("Quant Workbench")
    view = st.radio("Workspace", ["Single Stock", "Universe Screen", "Portfolio Backtest"], label_visibility="collapsed")

    st.markdown('<div class="section-title">Data</div>', unsafe_allow_html=True)
    provider_name = st.selectbox("Provider", ["csv", "auto", "yahoo", "akshare"], index=0)
    data_file = st.text_input("CSV file", "data/sample_prices.csv")
    cache_dir = st.text_input("Cache root", "data")
    use_cache = st.toggle("Use cache", value=True)
    adjust = st.selectbox("Adjust", ["qfq", "hfq", "none"], index=0)
    interval = st.selectbox("Online interval", ["1d", "1wk", "1mo"], index=0)
    start_raw = st.text_input("Start date", "")
    end_raw = st.text_input("End date", "")
    start = start_raw.strip() or None
    end = end_raw.strip() or None

    st.markdown('<div class="section-title">Config</div>', unsafe_allow_html=True)
    config_file = st.text_input("Config file", "configs/default.yaml")


st.title("Multi-Market Quant Workbench")


if view == "Single Stock":
    controls = st.columns([1.15, 1, 1, 1, 1])
    market = controls[0].selectbox("Market", ["cn", "hk", "us"], format_func=lambda value: MARKET_LABELS[value], index=2)
    symbol = controls[1].text_input("Symbol", MARKET_DEFAULTS[market])
    k_frequency = controls[2].selectbox("K-line frequency", ["Daily", "Weekly", "Monthly"], index=0)
    strategy_name = controls[3].selectbox("Strategy", ["ma", "rsi", "breakout"], index=0)
    run = controls[4].button("Run analysis", use_container_width=True, type="primary")

    strategy_cols = st.columns([1, 1, 1, 1])
    short_window = strategy_cols[0].number_input("Short MA", min_value=2, max_value=120, value=5)
    long_window = strategy_cols[1].number_input("Long MA", min_value=3, max_value=250, value=20)
    initial_cash = strategy_cols[2].number_input("Initial cash", min_value=1000, value=100000, step=10000)
    max_weight = strategy_cols[3].slider("Max weight", min_value=0.1, max_value=1.0, value=1.0, step=0.1)

    if run:
        prices = load_prices(
            provider_name,
            data_file,
            cache_dir,
            use_cache,
            symbol.strip(),
            market,
            start,
            end,
            adjust,
            interval,
        )
        chart_prices = resample_ohlcv(prices, k_frequency.lower())
        report = analyze_prices(prices)

        kpi_cols = st.columns(5)
        kpi_cols[0].metric("Close", f"{report['close']:.4f}")
        kpi_cols[1].metric("Score", f"{report['score']:.2f}/100")
        kpi_cols[2].metric("Trend", str(report["trend"]).title())
        kpi_cols[3].metric("20D Momentum", f"{report['signals']['momentum_20_pct']:.2f}%")
        kpi_cols[4].metric("20D Volatility", fmt_pct(float(report["signals"]["volatility_20"])))

        chart_tab, factor_tab, backtest_tab, risk_tab, data_tab = st.tabs(
            ["K Line", "Factors", "Backtest", "Risk", "Data"]
        )

        with chart_tab:
            st.plotly_chart(
                make_candlestick_figure(chart_prices, title=f"{symbol.upper()} {k_frequency} K Line"),
                use_container_width=True,
            )

        with factor_tab:
            left, right = st.columns([0.36, 0.64])
            with left:
                st.plotly_chart(make_score_gauge(float(report["score"])), use_container_width=True)
            with right:
                st.plotly_chart(make_factor_bar(report["signals"]), use_container_width=True)
            st.dataframe(metrics_frame(report["signals"]), use_container_width=True, hide_index=True)

        with backtest_tab:
            strategy = build_strategy(
                strategy_name,
                short_window=int(short_window),
                long_window=int(long_window),
                max_weight=float(max_weight),
            )
            result = BacktestEngine(BacktestConfig(initial_cash=float(initial_cash))).run(prices, strategy)
            st.plotly_chart(make_equity_drawdown_figure(result.equity_curve, title="Strategy vs Buy and Hold"), use_container_width=True)
            metric_cols = st.columns(5)
            metric_cols[0].metric("Total Return", fmt_pct(result.metrics["total_return"]))
            metric_cols[1].metric("Benchmark", fmt_pct(result.metrics["benchmark_total_return"]))
            metric_cols[2].metric("Sharpe", f"{result.metrics['sharpe']:.2f}")
            metric_cols[3].metric("Max Drawdown", fmt_pct(result.metrics["max_drawdown"]))
            metric_cols[4].metric("Trades", str(len(result.trades)))
            st.dataframe(metrics_frame(result.metrics), use_container_width=True, hide_index=True)
            if not result.trades.empty:
                st.dataframe(result.trades, use_container_width=True, hide_index=True)

        with risk_tab:
            risk_cols = st.columns(4)
            account_cash = risk_cols[0].number_input("Account cash", min_value=1000, value=100000, step=10000)
            risk_fraction = risk_cols[1].number_input("Risk per trade", min_value=0.001, max_value=0.2, value=0.02, step=0.005)
            stop_loss_pct = risk_cols[2].number_input("Stop loss", min_value=0.01, max_value=0.5, value=0.08, step=0.01)
            lot_size = risk_cols[3].number_input("Lot size", min_value=1, value=1)
            shares = fixed_fraction_position(
                cash=float(account_cash),
                price=float(report["close"]),
                risk_fraction=float(risk_fraction),
                stop_loss_pct=float(stop_loss_pct),
                lot_size=int(lot_size),
            )
            st.metric("Position size", f"{shares:,} shares")
            st.metric("Notional", f"{shares * float(report['close']):,.2f}")

        with data_tab:
            enriched = add_indicators(prices)
            st.dataframe(enriched.tail(120), use_container_width=True)

else:
    config = load_yaml(config_file)
    universe = parse_universe(config)
    provider = build_provider(provider_name, data_file, cache_dir, use_cache)

    if view == "Universe Screen":
        screen_cols = st.columns([1, 1, 1, 1])
        top = screen_cols[0].number_input("Top N", min_value=1, value=10)
        selected_markets = screen_cols[1].multiselect("Markets", ["cn", "hk", "us"], default=["cn", "hk", "us"])
        min_score = screen_cols[2].slider("Min score", min_value=0, max_value=100, value=0)
        run_screen = screen_cols[3].button("Run screen", use_container_width=True, type="primary")

        if run_screen:
            scoped = [security for security in universe if security.market.value in selected_markets]
            ranked = screen_universe(scoped, provider, start=start, end=end, top=int(top))
            filtered = ranked[ranked["score"] >= min_score].reset_index(drop=True)
            st.plotly_chart(make_screen_scatter(filtered), use_container_width=True)
            st.dataframe(filtered.drop(columns=["turnover_proxy"], errors="ignore"), use_container_width=True, hide_index=True)
            failures = ranked.attrs.get("failures", [])
            if failures:
                st.warning("\n".join(failures))

    else:
        portfolio_cols = st.columns([1, 1, 1, 1, 1])
        top_n = portfolio_cols[0].number_input("Hold Top N", min_value=1, value=int(config.get("portfolio", {}).get("top_n", 3)))
        rebalance = portfolio_cols[1].number_input(
            "Rebalance days",
            min_value=1,
            value=int(config.get("portfolio", {}).get("rebalance_frequency", 5)),
        )
        weighting = portfolio_cols[2].selectbox("Weighting", ["equal", "inverse_vol"], index=0)
        initial_cash = portfolio_cols[3].number_input("Initial cash", min_value=1000, value=100000, step=10000)
        run_portfolio = portfolio_cols[4].button("Run portfolio", use_container_width=True, type="primary")

        if run_portfolio:
            engine = PortfolioBacktestEngine(
                PortfolioBacktestConfig(
                    top_n=int(top_n),
                    rebalance_frequency=int(rebalance),
                    weighting=weighting,
                    initial_cash=float(initial_cash),
                )
            )
            result = engine.run(universe, provider, start=start, end=end)
            kpi_cols = st.columns(5)
            kpi_cols[0].metric("Total Return", fmt_pct(result.metrics["total_return"]))
            kpi_cols[1].metric("Excess", fmt_pct(result.metrics["excess_total_return"]))
            kpi_cols[2].metric("Sharpe", f"{result.metrics['sharpe']:.2f}")
            kpi_cols[3].metric("Max Drawdown", fmt_pct(result.metrics["max_drawdown"]))
            kpi_cols[4].metric("Rebalances", str(int(result.metrics["rebalance_count"])))
            st.plotly_chart(make_equity_drawdown_figure(result.equity_curve, title="Portfolio Equity"), use_container_width=True)
            st.plotly_chart(make_weights_figure(result.weights), use_container_width=True)
            detail_tab, metrics_tab = st.tabs(["Rebalance Log", "Metrics"])
            with detail_tab:
                st.dataframe(result.rebalance_log, use_container_width=True, hide_index=True)
            with metrics_tab:
                st.dataframe(metrics_frame(result.metrics), use_container_width=True, hide_index=True)
