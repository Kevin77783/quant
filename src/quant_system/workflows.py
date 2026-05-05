from __future__ import annotations

from dataclasses import dataclass

from quant_system.data import (
    AkShareProvider,
    AutoDataProvider,
    CachedDataProvider,
    CSVDataProvider,
    DataProvider,
    YahooFinanceProvider,
)


@dataclass(frozen=True)
class ProviderSettings:
    provider: str = "csv"
    data_file: str | None = "data/sample_prices.csv"
    cache_dir: str = "data"
    use_cache: bool = True


def build_data_provider(settings: ProviderSettings) -> DataProvider:
    """Build a data provider for CLI, Streamlit, examples, and future APIs."""

    normalized = settings.provider.strip().lower()
    if normalized == "csv":
        if not settings.data_file:
            raise ValueError("data_file is required for provider=csv.")
        return CSVDataProvider(settings.data_file)
    if normalized == "auto":
        return AutoDataProvider(settings.data_file, cache_dir=settings.cache_dir, use_cache=settings.use_cache)
    if normalized == "akshare":
        provider: DataProvider = AkShareProvider()
        return CachedDataProvider(provider, cache_dir=settings.cache_dir) if settings.use_cache else provider
    if normalized == "yahoo":
        provider = YahooFinanceProvider()
        return CachedDataProvider(provider, cache_dir=settings.cache_dir) if settings.use_cache else provider
    raise ValueError(f"Unknown provider: {settings.provider}")

