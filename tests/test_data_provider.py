from pathlib import Path

from quant_system.data import CSVDataProvider
from quant_system.models import Market, normalize_symbol


def test_csv_provider_filters_symbol_and_market() -> None:
    provider = CSVDataProvider(Path("data/sample_prices.csv"))

    data = provider.get_history("AAPL", Market.US)

    assert len(data) == 30
    assert set(data["symbol"]) == {"AAPL"}
    assert set(data["market"]) == {"us"}
    assert data.index.is_monotonic_increasing
    assert {"open", "high", "low", "close", "volume"}.issubset(data.columns)


def test_symbol_normalization_handles_common_market_suffixes() -> None:
    assert normalize_symbol("000001", "cn") == "000001.SZ"
    assert normalize_symbol("600519", "cn") == "600519.SH"
    assert normalize_symbol("700", "hk") == "0700.HK"
    assert normalize_symbol("aapl", "us") == "AAPL"

