from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from pathlib import Path

import pandas as pd

from quant_system.models import Market, normalize_ohlcv, normalize_symbol

logger = logging.getLogger(__name__)


class DataProvider(ABC):
    """Base class for historical market data providers."""

    @abstractmethod
    def get_history(
        self,
        symbol: str,
        market: str | Market,
        start: str | None = None,
        end: str | None = None,
        adjust: str = "qfq",
        interval: str = "1d",
    ) -> pd.DataFrame:
        raise NotImplementedError


class CSVDataProvider(DataProvider):
    """Load historical bars from one combined CSV file or a directory of CSV files."""

    def __init__(self, source: str | Path):
        self.source = Path(source)

    def get_history(
        self,
        symbol: str,
        market: str | Market,
        start: str | None = None,
        end: str | None = None,
        adjust: str = "qfq",
        interval: str = "1d",
    ) -> pd.DataFrame:
        parsed_market = Market.parse(market)
        normalized_symbol = normalize_symbol(symbol, parsed_market)
        frame = self._read_source(normalized_symbol)
        columns = {str(column).strip().lower(): column for column in frame.columns}

        if "symbol" in columns:
            raw_symbols = frame[columns["symbol"]].astype(str).str.strip().str.upper()
            frame = frame[raw_symbols == normalized_symbol]
        if "market" in columns:
            raw_markets = frame[columns["market"]].astype(str).str.strip().str.lower()
            frame = frame[raw_markets == parsed_market.value]

        data = normalize_ohlcv(frame, symbol=normalized_symbol, market=parsed_market)
        logger.info("Loaded %s %s from CSV source %s", normalized_symbol, parsed_market.value, self.source)
        return _filter_dates(data, start=start, end=end)

    def _read_source(self, normalized_symbol: str) -> pd.DataFrame:
        if self.source.is_file():
            return pd.read_csv(self.source)
        if self.source.is_dir():
            candidates = [
                self.source / f"{normalized_symbol}.csv",
                self.source / f"{normalized_symbol.replace('.', '_')}.csv",
                self.source / f"{normalized_symbol.split('.')[0]}.csv",
            ]
            for candidate in candidates:
                if candidate.exists():
                    return pd.read_csv(candidate)
        raise FileNotFoundError(f"No CSV data found for {normalized_symbol} under {self.source}")


class AkShareProvider(DataProvider):
    """AkShare provider for A-shares and selected Hong Kong equities."""

    def get_history(
        self,
        symbol: str,
        market: str | Market,
        start: str | None = None,
        end: str | None = None,
        adjust: str = "qfq",
        interval: str = "1d",
    ) -> pd.DataFrame:
        try:
            import akshare as ak
        except ImportError as exc:
            raise RuntimeError("akshare is not installed. Run: pip install -e '.[data]'") from exc

        parsed_market = Market.parse(market)
        start_date = _ak_date(start)
        end_date = _ak_date(end)
        if parsed_market == Market.CN:
            frame = ak.stock_zh_a_hist(
                symbol=_strip_exchange(symbol),
                period=_ak_period(interval),
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
            )
        elif parsed_market == Market.HK:
            frame = ak.stock_hk_hist(
                symbol=_strip_exchange(symbol).zfill(5),
                period=_ak_period(interval),
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
            )
        else:
            raise ValueError("AkShareProvider is intended for cn/hk. Use YahooFinanceProvider for us.")
        data = normalize_ohlcv(frame, symbol=symbol, market=parsed_market)
        logger.info("Loaded %s %s from AkShare", normalize_symbol(symbol, parsed_market), parsed_market.value)
        return data


class YahooFinanceProvider(DataProvider):
    """Yahoo Finance provider for US/HK equities and ETFs."""

    def get_history(
        self,
        symbol: str,
        market: str | Market,
        start: str | None = None,
        end: str | None = None,
        adjust: str = "qfq",
        interval: str = "1d",
    ) -> pd.DataFrame:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError("yfinance is not installed. Run: pip install -e '.[data]'") from exc

        parsed_market = Market.parse(market)
        ticker = _yahoo_symbol(symbol, parsed_market)
        history = yf.Ticker(ticker).history(
            start=start,
            end=end,
            interval=interval,
            auto_adjust=adjust not in {"none", "raw", ""},
        )
        if history.empty:
            raise RuntimeError(f"Yahoo Finance returned no data for {ticker}.")
        history = history.reset_index().rename(
            columns={
                "Date": "date",
                "Datetime": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        data = normalize_ohlcv(history, symbol=symbol, market=parsed_market)
        logger.info("Loaded %s %s from Yahoo Finance", normalize_symbol(symbol, parsed_market), parsed_market.value)
        return data


class DataCache:
    """Read and write canonical market data caches under data/raw and data/processed."""

    def __init__(self, root: str | Path = "data"):
        self.root = Path(root)
        self.raw_dir = self.root / "raw"
        self.processed_dir = self.root / "processed"

    def load(
        self,
        symbol: str,
        market: str | Market,
        start: str | None = None,
        end: str | None = None,
        adjust: str = "qfq",
        interval: str = "1d",
    ) -> pd.DataFrame | None:
        parsed_market = Market.parse(market)
        path = self._path(self.processed_dir, symbol, parsed_market, adjust, interval)
        if not path.exists():
            return None
        data = normalize_ohlcv(pd.read_csv(path), symbol=symbol, market=parsed_market)
        logger.info("Loaded %s %s from cache %s", normalize_symbol(symbol, parsed_market), parsed_market.value, path)
        return _filter_dates(data, start=start, end=end)

    def save(
        self,
        frame: pd.DataFrame,
        symbol: str,
        market: str | Market,
        adjust: str = "qfq",
        interval: str = "1d",
        provider_name: str = "online",
    ) -> None:
        parsed_market = Market.parse(market)
        data = normalize_ohlcv(frame, symbol=symbol, market=parsed_market)
        for base_dir in (self.raw_dir, self.processed_dir):
            path = self._path(base_dir, symbol, parsed_market, adjust, interval)
            path.parent.mkdir(parents=True, exist_ok=True)
            cached = data.copy()
            cached["provider"] = provider_name
            cached.to_csv(path, index=False)
            logger.info("Cached %s %s data to %s", normalize_symbol(symbol, parsed_market), parsed_market.value, path)

    def _path(self, base_dir: Path, symbol: str, market: Market, adjust: str, interval: str) -> Path:
        normalized = normalize_symbol(symbol, market).replace(".", "_")
        safe_adjust = str(adjust or "none").replace("/", "_")
        safe_interval = str(interval or "1d").replace("/", "_")
        return base_dir / market.value / f"{normalized}_{safe_interval}_{safe_adjust}.csv"


class CachedDataProvider(DataProvider):
    """Wrap another provider and persist successful online responses."""

    def __init__(
        self,
        provider: DataProvider,
        cache_dir: str | Path = "data",
        fallback_to_cache: bool = False,
    ):
        self.provider = provider
        self.cache = DataCache(cache_dir)
        self.fallback_to_cache = fallback_to_cache

    def get_history(
        self,
        symbol: str,
        market: str | Market,
        start: str | None = None,
        end: str | None = None,
        adjust: str = "qfq",
        interval: str = "1d",
    ) -> pd.DataFrame:
        try:
            data = self.provider.get_history(symbol, market, start, end, adjust, interval)
            self.cache.save(
                data,
                symbol=symbol,
                market=market,
                adjust=adjust,
                interval=interval,
                provider_name=self.provider.__class__.__name__,
            )
            return data
        except Exception:
            if not self.fallback_to_cache:
                raise
            cached = self.cache.load(symbol, market, start, end, adjust, interval)
            if cached is None:
                raise
            return cached


class AutoDataProvider(DataProvider):
    """Try online providers first, then cache and local CSV fallback."""

    def __init__(
        self,
        local_source: str | Path | None = None,
        cache_dir: str | Path = "data",
        use_cache: bool = True,
    ):
        self.local_source = Path(local_source) if local_source else None
        self.cache = DataCache(cache_dir) if use_cache else None

    def get_history(
        self,
        symbol: str,
        market: str | Market,
        start: str | None = None,
        end: str | None = None,
        adjust: str = "qfq",
        interval: str = "1d",
    ) -> pd.DataFrame:
        parsed_market = Market.parse(market)
        providers = self._online_providers(parsed_market)

        errors: list[str] = []
        for provider in providers:
            try:
                data = provider.get_history(symbol, parsed_market, start, end, adjust, interval)
                if self.cache:
                    self.cache.save(
                        data,
                        symbol=symbol,
                        market=parsed_market,
                        adjust=adjust,
                        interval=interval,
                        provider_name=provider.__class__.__name__,
                    )
                return data
            except Exception as exc:  # pragma: no cover - optional providers/network vary by environment.
                logger.warning("%s failed for %s %s: %s", provider.__class__.__name__, symbol, parsed_market.value, exc)
                errors.append(f"{provider.__class__.__name__}: {exc}")

        if self.cache:
            try:
                cached = self.cache.load(symbol, parsed_market, start, end, adjust, interval)
                if cached is not None:
                    return cached
            except Exception as exc:
                logger.warning("Cache failed for %s %s: %s", symbol, parsed_market.value, exc)
                errors.append(f"DataCache: {exc}")

        if self.local_source and self.local_source.exists():
            try:
                return CSVDataProvider(self.local_source).get_history(symbol, parsed_market, start, end, adjust, interval)
            except Exception as exc:
                logger.warning("Local CSV fallback failed for %s %s: %s", symbol, parsed_market.value, exc)
                errors.append(f"CSVDataProvider: {exc}")

        joined = "\n".join(errors)
        raise RuntimeError(f"All data providers failed for {symbol} ({parsed_market.value}):\n{joined}")

    def _online_providers(self, market: Market) -> list[DataProvider]:
        if market == Market.CN:
            return [AkShareProvider(), YahooFinanceProvider()]
        if market == Market.HK:
            return [YahooFinanceProvider(), AkShareProvider()]
        return [YahooFinanceProvider()]


def _filter_dates(frame: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
    data = frame
    if start:
        data = data[data["date"] >= pd.Timestamp(start)]
    if end:
        data = data[data["date"] <= pd.Timestamp(end)]
    if data.empty:
        raise ValueError("No rows left after applying date filters.")
    return data


def _strip_exchange(symbol: str) -> str:
    return str(symbol).strip().upper().split(".")[0]


def _ak_date(value: str | None) -> str:
    if not value:
        return "19900101"
    return pd.Timestamp(value).strftime("%Y%m%d")


def _ak_period(interval: str) -> str:
    mapping = {"1d": "daily", "1wk": "weekly", "1mo": "monthly"}
    return mapping.get(interval, interval)


def _yahoo_symbol(symbol: str, market: Market) -> str:
    normalized = normalize_symbol(symbol, market)
    if market == Market.HK and normalized.endswith(".HK"):
        return normalized
    if market == Market.CN:
        return normalized
    return normalized.replace(".US", "")
