from quant_system.backtest import BacktestConfig, BacktestEngine
from quant_system.data import CSVDataProvider
from quant_system.strategies import MovingAverageCrossStrategy


def test_backtest_engine_generates_equity_curve_and_metrics() -> None:
    prices = CSVDataProvider("data/sample_prices.csv").get_history("AAPL", "us")
    strategy = MovingAverageCrossStrategy(short_window=5, long_window=20)
    engine = BacktestEngine(BacktestConfig(initial_cash=100000, commission_bps=2, slippage_bps=1))

    result = engine.run(prices, strategy)

    assert len(result.equity_curve) == len(prices)
    assert result.equity_curve["equity"].iloc[0] == 100000
    assert result.equity_curve["equity"].iloc[-1] > 0
    assert "total_return" in result.metrics
    assert "benchmark_total_return" in result.metrics
    assert set(result.signals.columns).issuperset({"date", "target_weight", "reason"})

