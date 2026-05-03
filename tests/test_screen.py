from quant_system.analysis import screen_universe
from quant_system.config import load_yaml, parse_universe
from quant_system.data import CSVDataProvider


def test_screen_universe_ranks_configured_markets() -> None:
    config = load_yaml("configs/default.yaml")
    universe = parse_universe(config)
    provider = CSVDataProvider("data/sample_prices.csv")

    ranked = screen_universe(universe, provider, top=3)

    assert len(ranked) == 3
    assert list(ranked["rank"]) == [1, 2, 3]
    assert set(ranked["market"]) == {"cn", "hk", "us"}
    assert ranked["score"].between(0, 100).all()

