from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd

from quant_system.models import Market, normalize_ohlcv, normalize_symbol


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
        return normalize_ohlcv(frame, symbol=symbol, market=parsed_market)


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
        return normalize_ohlcv(history, symbol=symbol, market=parsed_market)


class AutoDataProvider(DataProvider):
    """Try local data first, then market-appropriate online providers."""

    def __init__(self, local_source: str | Path | None = None):
        self.local_source = Path(local_source) if local_source else None

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
        providers: list[DataProvider] = []
        if self.local_source and self.local_source.exists():
            providers.append(CSVDataProvider(self.local_source))
        if parsed_market == Market.CN:
            providers.extend([AkShareProvider(), YahooFinanceProvider()])
        elif parsed_market == Market.HK:
            providers.extend([YahooFinanceProvider(), AkShareProvider()])
        else:
            providers.append(YahooFinanceProvider())

        errors: list[str] = []
        for provider in providers:
            try:
                return provider.get_history(symbol, parsed_market, start, end, adjust, interval)
            except Exception as exc:  # pragma: no cover - error aggregation depends on optional providers/network.
                errors.append(f"{provider.__class__.__name__}: {exc}")
        joined = "\n".join(errors)
        raise RuntimeError(f"All data providers failed for {symbol} ({parsed_market.value}):\n{joined}")


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

