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


def shorten_asset(symbol: str, *, head: int = 6, tail: int = 4, min_length: int = 16) -> str:
    """Condense long token identifiers (e.g., contract addresses) for display."""

    if not symbol or len(symbol) < min_length:
        return symbol

    prefix = symbol[:head]
    suffix = symbol[-tail:]
    return f"{prefix}...{suffix}"
