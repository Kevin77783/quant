from quant_system.backtest import PortfolioBacktestConfig, PortfolioBacktestEngine
from quant_system.config import load_yaml, parse_universe
from quant_system.data import CSVDataProvider


def test_portfolio_backtest_runs_with_sample_universe() -> None:
    config = load_yaml("configs/default.yaml")
    universe = parse_universe(config)
    provider = CSVDataProvider("data/sample_prices.csv")
    engine = PortfolioBacktestEngine(
        PortfolioBacktestConfig(initial_cash=100000, top_n=2, rebalance_frequency=5, weighting="equal")
    )

    result = engine.run(universe, provider)

    assert len(result.equity_curve) == 30
    assert result.equity_curve["equity"].iloc[-1] > 0
    assert result.metrics["loaded_symbols"] == 3
    assert result.metrics["failed_symbols"] == 3
    assert "AAPL" in result.weights.columns
    assert not result.rebalance_log.empty

