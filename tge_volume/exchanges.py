"""Helpers for building a ccxt-compatible market list and fetching OHLCV data."""
from __future__ import annotations

from typing import Any, Dict, List

import ccxt

from .utils import is_dex_name

EXCHANGE_NAME_TO_CCXT_ID = {
    "Binance": "binance",
    "Binance US": "binanceus",
    "OKX": "okx",
    "OKX (Spot)": "okx",
    "Bybit": "bybit",
    "KuCoin": "kucoin",
    "Gate": "gateio",
    "Gate.io": "gateio",
    "Gate (Spot)": "gateio",
    "MEXC": "mexc",
    "Bitget": "bitget",
    "Coinbase Exchange": "coinbase",
    "Kraken": "kraken",
    "Uniswap V2": "uniswap",
    "Uniswap V3 (Ethereum)": "uniswap",
    "PancakeSwap (v2)": "pancakeswap",
}



def build_markets(tickers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a deduplicated list of markets with volume metadata."""
    markets: Dict[str, Dict[str, Any]] = {}

    for ticker in tickers:
        name = ticker.get("market", {}).get("name")
        if not name:
            continue

        base = ticker.get("base")
        quote = ticker.get("target")
        if not base or not quote:
            continue

        volume = ticker.get("volume") or 0
        if name not in markets or volume > markets[name]["volume"]:
            markets[name] = {
                "exchange_name": name,
                "base": base,
                "quote": quote,
                "volume": volume,
                "is_dex": is_dex_name(name),
                "ccxt_id": EXCHANGE_NAME_TO_CCXT_ID.get(name),
            }

    return list(markets.values())



def fetch_exchange_stats(
    exchange_id: str,
    base: str,
    quote: str,
    expected_tge_ts: int | None = None,
) -> Dict[str, Any]:
    """Fetch the earliest available OHLCV candle for the pair."""
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class()
    exchange.load_markets()

    symbol_candidates = [f"{base}/{quote}", f"{base.upper()}/{quote.upper()}"]
    symbol = next((candidate for candidate in symbol_candidates if candidate in exchange.markets), None)
    if not symbol:
        raise RuntimeError(f"Пара {base}/{quote} не найдена на {exchange_id}")

    try:
        oldest = exchange.fetch_ohlcv(symbol, timeframe="15m", limit=1)
        if not oldest:
            raise RuntimeError("Биржа не вернула OHLCV")
        oldest_ts, oldest_open, _, _, _, oldest_vol = oldest[0]
    except Exception as exc:  # pragma: no cover - network errors
        raise RuntimeError(f"Не удалось получить самую раннюю свечу: {exc}") from exc

    if expected_tge_ts and oldest_ts > expected_tge_ts:
        return {
            "tge_ts": oldest_ts,
            "tge_open": oldest_open,
            "first_15m_volume": oldest_vol,
            "day_open": None,
            "day_high": None,
            "day_delta_ratio": None,
            "note": "История биржи начинается ПОСЛЕ TGE — реальный TGE недоступен",
        }

    try:
        day = exchange.fetch_ohlcv(symbol, timeframe="1d", since=oldest_ts, limit=1)
        if day:
            day_open = day[0][1]
            day_high = day[0][2]
            day_delta = (day_high / day_open) if day_open else None
        else:
            day_open = day_high = day_delta = None
    except Exception:  # pragma: no cover - network errors
        day_open = day_high = day_delta = None

    return {
        "tge_ts": oldest_ts,
        "tge_open": oldest_open,
        "first_15m_volume": oldest_vol,
        "day_open": day_open,
        "day_high": day_high,
        "day_delta_ratio": day_delta,
        "note": None,
    }
