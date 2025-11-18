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
    "BitMart": "bitmart",
    "Bitget": "bitget",
    "Coinbase Exchange": "coinbase",
    "Kraken": "kraken",
    "Uniswap V2": "uniswap",
    "Uniswap V3 (Ethereum)": "uniswap",
    "PancakeSwap (v2)": "pancakeswap",
}

# Allow selectively disabling exchanges (e.g., for temporary outages) while
# still showing them in the CLI output.
DISABLED_EXCHANGES: Dict[str, str] = {}

def build_markets(tickers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a deduplicated list of markets with volume metadata."""
    markets: Dict[str, Dict[str, Any]] = {}

    for ticker in tickers:
        name = ticker.get("market", {}).get("name")
        if not name:
            continue

        if is_dex_name(name):
            # The CLI focuses on centralized exchanges only, so skip DEX entries
            continue

        base = ticker.get("base")
        quote = ticker.get("target")
        if not base or not quote:
            continue

        volume = ticker.get("volume") or 0
        if name not in markets or volume > markets[name]["volume"]:
            disabled_reason = DISABLED_EXCHANGES.get(name)
            markets[name] = {
                "exchange_name": name,
                "base": base,
                "quote": quote,
                "volume": volume,
                "ccxt_id": None if disabled_reason else EXCHANGE_NAME_TO_CCXT_ID.get(name),
                "disabled_reason": disabled_reason,
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

    normalized_base = base.upper()
    normalized_quote = quote.upper()

    def _matching_markets(prefer_spot: bool) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        for market in exchange.markets.values():
            market_base = market.get("base")
            market_quote = market.get("quote")
            if not market_base or not market_quote:
                continue
            if market_base.upper() == normalized_base and market_quote.upper() == normalized_quote:
                if not prefer_spot or market.get("spot"):
                    matches.append(market)
        return matches

    spot_matches = _matching_markets(prefer_spot=True)
    derivative_matches = _matching_markets(prefer_spot=False)

    market = None
    if spot_matches:
        market = spot_matches[0]
    elif derivative_matches:
        market = derivative_matches[0]

    if not market:
        raise RuntimeError(f"Пара {base}/{quote} не найдена на {exchange_id}")

    symbol = market["symbol"]

    timeframe = "15m"
    timeframe_ms = exchange.parse_timeframe(timeframe) * 1000
    limit = exchange.options.get("OHLCVLimit") or 500
    since_ts = exchange.milliseconds() - timeframe_ms * limit

    last_non_empty_batch: List[List[float]] | None = None

    try:
        while True:
            candles = exchange.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                since=since_ts,
                limit=limit,
            )
            if not candles:
                break

            if (
                last_non_empty_batch is not None
                and candles[0][0] == last_non_empty_batch[0][0]
            ):
                break

            last_non_empty_batch = candles
            since_ts -= timeframe_ms * limit

        if not last_non_empty_batch:
            raise RuntimeError("Биржа не вернула OHLCV")

        (
            oldest_ts,
            oldest_open,
            oldest_high,
            oldest_low,
            oldest_close,
            oldest_vol,
        ) = last_non_empty_batch[0]

        reference_price = next(
            (
                price
                for price in [oldest_close, oldest_open, oldest_high, oldest_low]
                if price
            ),
            None,
        )

        first_15m_volume_quote = (
            oldest_vol * reference_price if oldest_vol and reference_price else None
        )
    except Exception as exc:  # pragma: no cover - network errors
        raise RuntimeError(f"Не удалось получить самую раннюю свечу: {exc}") from exc

    if expected_tge_ts and oldest_ts > expected_tge_ts:
        return {
            "tge_ts": oldest_ts,
            "tge_open": oldest_open,
            "first_15m_volume": first_15m_volume_quote,
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
        "first_15m_volume": first_15m_volume_quote,
        "day_open": day_open,
        "day_high": day_high,
        "day_delta_ratio": day_delta,
        "note": None,
    }
