from quant_system.analysis import analyze_prices, screen_universe
from quant_system.backtest import BacktestConfig, BacktestEngine, PortfolioBacktestConfig, PortfolioBacktestEngine
from quant_system.config import load_yaml, parse_universe
from quant_system.data import CSVDataProvider
from quant_system.strategies import MovingAverageCrossStrategy


def main() -> None:
    provider = CSVDataProvider("data/sample_prices.csv")

    prices = provider.get_history("AAPL", "us")
    print(analyze_prices(prices))

    strategy = MovingAverageCrossStrategy(short_window=5, long_window=20)
    result = BacktestEngine(BacktestConfig(initial_cash=100000)).run(prices, strategy)
    print(result.metrics)

    universe = parse_universe(load_yaml("configs/default.yaml"))
    print(screen_universe(universe, provider, top=3))

    portfolio = PortfolioBacktestEngine(
        PortfolioBacktestConfig(top_n=2, rebalance_frequency=5, weighting="equal")
    ).run(universe, provider)
    print(portfolio.metrics)


if __name__ == "__main__":
    main()
