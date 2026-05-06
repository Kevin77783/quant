from quant_system.analysis import AlertRule, compare_universe, scan_alerts
from quant_system.backtest import BacktestConfig, optimize_ma_strategy
from quant_system.config import load_yaml, parse_universe
from quant_system.data import CSVDataProvider


def test_compare_universe_builds_summary_normalized_and_correlation() -> None:
    config = load_yaml("configs/default.yaml")
    universe = parse_universe(config)
    provider = CSVDataProvider("data/sample_prices.csv")

    result = compare_universe(universe, provider)

    assert set(result.summary["symbol"]) == {"000001.SZ", "0700.HK", "AAPL"}
    assert {"symbol", "total_return", "annual_volatility", "sharpe", "current_drawdown"}.issubset(
        result.summary.columns
    )
    assert {"date", "000001.SZ", "0700.HK", "AAPL"}.issubset(result.normalized.columns)
    assert result.normalized[["000001.SZ", "0700.HK", "AAPL"]].iloc[0].eq(100.0).all()
    assert set(result.correlation.columns) == {"000001.SZ", "0700.HK", "AAPL"}
    assert len(result.failures) == 3


def test_scan_alerts_can_return_all_rows_and_failures() -> None:
    config = load_yaml("configs/default.yaml")
    universe = parse_universe(config)
    provider = CSVDataProvider("data/sample_prices.csv")

    alerts = scan_alerts(universe, provider, rule=AlertRule(include_all=True))

    assert set(alerts["symbol"]) == {"000001.SZ", "0700.HK", "AAPL"}
    assert {"trigger_count", "alerts", "score", "rsi", "drawdown"}.issubset(alerts.columns)
    assert alerts["trigger_count"].ge(0).all()
    assert len(alerts.attrs["failures"]) == 3


def test_optimize_ma_strategy_ranks_parameter_grid() -> None:
    provider = CSVDataProvider("data/sample_prices.csv")
    prices = provider.get_history("AAPL", "us")

    results = optimize_ma_strategy(
        prices,
        short_windows=(3, 5, 20),
        long_windows=(10, 20),
        config=BacktestConfig(initial_cash=100000, commission_bps=2, slippage_bps=1),
        rank_metric="sharpe",
    )

    assert not results.empty
    assert {"short_window", "long_window", "sharpe", "total_return", "trades"}.issubset(results.columns)
    assert (results["short_window"] < results["long_window"]).all()
    assert results["sharpe"].is_monotonic_decreasing
