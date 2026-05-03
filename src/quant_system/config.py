from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from quant_system.models import Security


def load_yaml(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {config_path}")
    return data


def parse_universe(config: dict[str, Any]) -> list[Security]:
    raw_items = config.get("universe", [])
    if not isinstance(raw_items, list):
        raise ValueError("Config field 'universe' must be a list.")

    universe: list[Security] = []
    for item in raw_items:
        if isinstance(item, str):
            symbol, market = _parse_symbol_market(item)
            universe.append(Security.from_raw(symbol=symbol, market=market))
            continue
        if not isinstance(item, dict):
            raise ValueError(f"Invalid universe item: {item!r}")
        universe.append(
            Security.from_raw(
                symbol=str(item["symbol"]),
                market=str(item["market"]),
                name=item.get("name"),
            )
        )
    return universe


def parse_universe_argument(raw: str) -> list[Security]:
    if not raw.strip():
        return []
    universe = []
    for item in raw.split(","):
        symbol, market = _parse_symbol_market(item)
        universe.append(Security.from_raw(symbol=symbol, market=market))
    return universe


def _parse_symbol_market(raw: str) -> tuple[str, str]:
    parts = [part.strip() for part in raw.split(":")]
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"Universe item must be formatted as SYMBOL:market, got {raw!r}")
    return parts[0], parts[1]

