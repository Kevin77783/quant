from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

import pandas as pd


class Market(str, Enum):
    """Supported equity markets."""

    CN = "cn"
    HK = "hk"
    US = "us"

    @classmethod
    def parse(cls, value: str | "Market") -> "Market":
        if isinstance(value, Market):
            return value
        normalized = str(value).strip().lower()
        aliases = {
            "a": cls.CN,
            "ashare": cls.CN,
            "a-share": cls.CN,
            "china": cls.CN,
            "cn": cls.CN,
            "hk": cls.HK,
            "hkg": cls.HK,
            "hongkong": cls.HK,
            "hong-kong": cls.HK,
            "us": cls.US,
            "usa": cls.US,
            "nasdaq": cls.US,
            "nyse": cls.US,
            "amex": cls.US,
        }
        if normalized not in aliases:
            raise ValueError(f"Unsupported market: {value!r}. Use one of cn, hk, us.")
        return aliases[normalized]


@dataclass(frozen=True)
class Security:
    symbol: str
    market: Market
    name: str | None = None

    @classmethod
    def from_raw(cls, symbol: str, market: str | Market, name: str | None = None) -> "Security":
        return cls(symbol=normalize_symbol(symbol, market), market=Market.parse(market), name=name)


REQUIRED_PRICE_COLUMNS = ("date", "open", "high", "low", "close", "volume")

_COLUMN_ALIASES = {
    "日期": "date",
    "交易日期": "date",
    "time": "date",
    "datetime": "date",
    "timestamp": "date",
    "开盘": "open",
    "开盘价": "open",
    "open": "open",
    "最高": "high",
    "最高价": "high",
    "high": "high",
    "最低": "low",
    "最低价": "low",
    "low": "low",
    "收盘": "close",
    "收盘价": "close",
    "close": "close",
    "成交量": "volume",
    "volume": "volume",
    "vol": "volume",
    "代码": "symbol",
    "证券代码": "symbol",
    "symbol": "symbol",
    "市场": "market",
    "market": "market",
}


def normalize_symbol(symbol: str, market: str | Market) -> str:
    """Normalize a symbol for internal use without hiding its exchange suffix."""

    parsed = Market.parse(market)
    raw = str(symbol).strip().upper()
    if parsed == Market.HK and raw.isdigit():
        return raw.zfill(4) + ".HK"
    if parsed == Market.CN and raw.isdigit():
        if raw.startswith(("5", "6", "9")):
            return raw + ".SH"
        if raw.startswith(("0", "2", "3")):
            return raw + ".SZ"
        if raw.startswith(("4", "8")):
            return raw + ".BJ"
    return raw


def normalize_ohlcv(
    frame: pd.DataFrame,
    symbol: str | None = None,
    market: str | Market | None = None,
) -> pd.DataFrame:
    """Return a clean OHLCV frame with a DatetimeIndex and canonical columns."""

    if frame.empty:
        raise ValueError("Price frame is empty.")

    data = frame.copy()
    renamed: dict[Any, str] = {}
    for column in data.columns:
        key = str(column).strip()
        lower_key = key.lower()
        renamed[column] = _COLUMN_ALIASES.get(key, _COLUMN_ALIASES.get(lower_key, lower_key))
    data = data.rename(columns=renamed)

    if "date" not in data.columns and isinstance(data.index, pd.DatetimeIndex):
        data["date"] = data.index
    data = data.reset_index(drop=True)

    missing = [column for column in REQUIRED_PRICE_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError(f"Price frame missing required columns: {missing}")

    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.dropna(subset=["date"]).copy()
    for column in ("open", "high", "low", "close", "volume"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.dropna(subset=["open", "high", "low", "close"]).copy()
    data["volume"] = data["volume"].fillna(0.0)

    if symbol is not None:
        parsed_market = market if market is not None else data.get("market", pd.Series(["us"])).iloc[0]
        data["symbol"] = normalize_symbol(symbol, parsed_market)
    elif "symbol" in data.columns:
        data["symbol"] = data["symbol"].astype(str).str.strip().str.upper()

    if market is not None:
        data["market"] = Market.parse(market).value
    elif "market" in data.columns:
        data["market"] = data["market"].astype(str).str.strip().str.lower()

    keep = ["date", "symbol", "market", "open", "high", "low", "close", "volume"]
    ordered = [column for column in keep if column in data.columns]
    extras = [column for column in data.columns if column not in ordered]
    data = data[ordered + extras].sort_values("date").drop_duplicates(subset=["date"], keep="last")
    data = data.set_index("date", drop=False)
    return data
