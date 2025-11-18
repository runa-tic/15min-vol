"""Shared helper utilities for the TGE analysis CLI."""
from __future__ import annotations

from datetime import datetime, timezone


def is_dex_name(name: str) -> bool:
    """Return ``True`` when the given market name is a DEX."""
    normalized = name.lower()
    return any(term in normalized for term in ("swap", "uniswap", "pancake", "sushiswap"))


def ts_to_str(ts: int | None) -> str:
    """Pretty-print a millisecond unix timestamp in UTC."""
    if not ts:
        return "-"
    dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
