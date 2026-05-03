import pandas as pd
import pytest

from quant_system.data import AutoDataProvider, CachedDataProvider, DataProvider
from quant_system.models import normalize_ohlcv


class StaticProvider(DataProvider):
    def __init__(self, close: float):
        self.close = close

    def get_history(self, symbol, market, start=None, end=None, adjust="qfq", interval="1d"):
        return pd.DataFrame(
            {
                "date": ["2025-01-02", "2025-01-03"],
                "symbol": [symbol, symbol],
                "market": [market, market],
                "open": [self.close, self.close],
                "high": [self.close + 1, self.close + 1],
                "low": [self.close - 1, self.close - 1],
                "close": [self.close, self.close],
                "volume": [1000, 1200],
            }
        )


def test_cached_provider_writes_raw_and_processed_cache(tmp_path) -> None:
    provider = CachedDataProvider(StaticProvider(10.0), cache_dir=tmp_path)

    data = provider.get_history("AAPL", "us")

    assert data["close"].iloc[-1] == 10.0
    assert list((tmp_path / "raw" / "us").glob("AAPL_1d_qfq.csv"))
    assert list((tmp_path / "processed" / "us").glob("AAPL_1d_qfq.csv"))


def test_auto_provider_prefers_online_before_local_sample(tmp_path) -> None:
    provider = AutoDataProvider(local_source="data/sample_prices.csv", cache_dir=tmp_path, use_cache=True)
    provider._online_providers = lambda market: [StaticProvider(99.0)]  # type: ignore[method-assign]

    data = provider.get_history("AAPL", "us")

    assert data["close"].iloc[-1] == 99.0


def test_normalize_ohlcv_rejects_invalid_price_ranges() -> None:
    bad = pd.DataFrame(
        {
            "date": ["2025-01-02"],
            "open": [10],
            "high": [7],
            "low": [8],
            "close": [8.5],
            "volume": [1000],
        }
    )

    with pytest.raises(ValueError, match="high is lower than low"):
        normalize_ohlcv(bad, symbol="AAPL", market="us")
