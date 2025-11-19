"""Helpers for building a ccxt-compatible market list and fetching OHLCV data."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

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
    "BitMart": "bitmart",
    "BingX": "bingx",
    "LBank": "lbank",
    "Poloniex": "poloniex",
}

# Some exchanges require special setup to ensure we talk to the spot API.
EXCHANGE_SETUP_OVERRIDES: Dict[str, Dict[str, Any]] = {
    "bitmart": {
        "options": {
            "defaultType": "spot",
            "fetchOHLCV": {"type": "spot"},
        }
    }
}

EXCHANGE_FETCH_OHLCV_PARAMS: Dict[str, Dict[str, Any]] = {
    "bitmart": {"type": "spot"},
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



def _prepare_exchange_market(
    exchange_id: str, base: str, quote: str, timeframe: str = "15m"
) -> Tuple[ccxt.Exchange, str, int, int, Dict[str, Any]]:
    """Return an initialized exchange, symbol and OHLCV fetch config."""

    exchange_class = getattr(ccxt, exchange_id)
    exchange_kwargs = EXCHANGE_SETUP_OVERRIDES.get(exchange_id, {})
    exchange = exchange_class(exchange_kwargs)
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
    timeframe_ms = exchange.parse_timeframe(timeframe) * 1000
    limit = exchange.options.get("OHLCVLimit") or 500
    fetch_params = EXCHANGE_FETCH_OHLCV_PARAMS.get(exchange_id, {})

    return exchange, symbol, timeframe_ms, limit, fetch_params


def _collect_full_ohlcv(
    exchange: ccxt.Exchange,
    symbol: str,
    timeframe: str,
    timeframe_ms: int,
    limit: int,
    fetch_params: Dict[str, Any],
) -> List[List[float]]:
    """Fetch the full available OHLCV history for the given symbol."""

    earliest_batch: List[List[float]] | None = None
    probe_since = exchange.milliseconds() - timeframe_ms * limit
    while True:
        candles = exchange.fetch_ohlcv(
            symbol,
            timeframe=timeframe,
            since=probe_since,
            limit=limit,
            params=fetch_params,
        )
        if not candles:
            break
        if earliest_batch is not None and candles[0][0] == earliest_batch[0][0]:
            break
        earliest_batch = candles
        probe_since -= timeframe_ms * limit

    if not earliest_batch:
        return []

    all_candles: List[List[float]] = []
    next_since = earliest_batch[0][0]
    last_first_ts = None

    while True:
        candles = exchange.fetch_ohlcv(
            symbol,
            timeframe=timeframe,
            since=next_since,
            limit=limit,
            params=fetch_params,
        )
        if not candles:
            break
        if last_first_ts is not None and candles[0][0] == last_first_ts:
            break

        last_first_ts = candles[0][0]
        all_candles.extend(candles)
        next_since = candles[-1][0] + timeframe_ms

        if len(candles) < limit:
            break

    dedup = {candle[0]: candle for candle in all_candles}
    return [dedup[ts] for ts in sorted(dedup)]


def fetch_exchange_stats(
    exchange_id: str,
    base: str,
    quote: str,
    expected_tge_ts: int | None = None,
) -> Dict[str, Any]:
    """Fetch the earliest available OHLCV candle for the pair."""

    (
        exchange,
        symbol,
        timeframe_ms,
        limit,
        fetch_params,
    ) = _prepare_exchange_market(exchange_id, base, quote)
    timeframe = "15m"

    try:
        candles = _collect_full_ohlcv(
            exchange,
            symbol,
            timeframe,
            timeframe_ms,
            limit,
            fetch_params,
        )

        if not candles:
            raise RuntimeError("Биржа не вернула OHLCV")

        target_candle = candles[0]

        (
            oldest_ts,
            oldest_open,
            oldest_high,
            oldest_low,
            oldest_close,
            oldest_vol,
        ) = target_candle

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
        day_timeframe_ms = exchange.parse_timeframe("1d") * 1000
        target_ts = oldest_ts
        # Request a window that surely covers the target TGE day.  Some
        # exchanges round the `since` argument down to daily boundaries and
        # return the *previous* day when `since` is close to midnight.  By
        # asking for a slightly earlier window (two days back) and then
        # picking the candle that actually contains the target timestamp we
        # avoid mismatches (e.g., reporting the day before/after TGE).
        day_since_ts = (target_ts or oldest_ts) - day_timeframe_ms * 2
        day = exchange.fetch_ohlcv(
            symbol,
            timeframe="1d",
            since=day_since_ts,
            limit=10,
            params=fetch_params,
        )

        day_open = day_high = day_delta = None
        if day:
            day_candle = None
            for candle in day:
                start = candle[0]
                if start <= target_ts < start + day_timeframe_ms:
                    day_candle = candle
                    break

            if not day_candle:
                # Fallback to the latest candle before the target timestamp,
                # or the first candle if the exchange returned only newer
                # data.  This mirrors the old behaviour but only when we fail
                # to confidently identify the TGE day.
                eligible = [c for c in day if c[0] <= target_ts]
                day_candle = max(eligible, key=lambda c: c[0], default=day[0])

            day_open = day_candle[1]
            day_high = day_candle[2]
            # The CLI reports the "HIGH/OPEN" metric as the multiplier
            # between the first day's high and the launch (TGE) open.
            day_delta = (day_high / oldest_open) if oldest_open else None
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


def fetch_trading_flow(
    exchange_id: str, base: str, quote: str, timeframe: str = "15m"
) -> List[List[float]]:
    """Return the full 15m trading flow for debugging purposes."""

    (
        exchange,
        symbol,
        timeframe_ms,
        limit,
        fetch_params,
    ) = _prepare_exchange_market(exchange_id, base, quote, timeframe=timeframe)

    try:
        return _collect_full_ohlcv(
            exchange,
            symbol,
            timeframe,
            timeframe_ms,
            limit,
            fetch_params,
        )
    except Exception as exc:  # pragma: no cover - network errors
        raise RuntimeError(
            f"Не удалось выгрузить полную историю свечей {timeframe}: {exc}"
        ) from exc
