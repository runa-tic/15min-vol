"""Minimal wrapper around the CoinGecko REST API."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import requests

COINGECKO_API = "https://api.coingecko.com/api/v3"


def search_token(symbol: str) -> List[Dict[str, Any]]:
    """Return CoinGecko projects matching the given ticker symbol."""
    response = requests.get(f"{COINGECKO_API}/search", params={"query": symbol})
    response.raise_for_status()
    data = response.json()
    return [c for c in data["coins"] if c.get("symbol", "").lower() == symbol.lower()]


def get_coin_tickers(coin_id: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Fetch tickers for a project and return the raw CoinGecko payload."""
    response = requests.get(
        f"{COINGECKO_API}/coins/{coin_id}",
        params={
            "localization": "false",
            "tickers": "true",
            "market_data": "false",
            "community_data": "false",
            "developer_data": "false",
            "sparkline": "false",
        },
    )
    response.raise_for_status()
    data = response.json()
    return data["tickers"], data


def get_expected_tge_ts(coin_data: Dict[str, Any]) -> int | None:
    """Best-effort guess for the TGE timestamp according to CoinGecko."""
    genesis = coin_data.get("genesis_date")
    if genesis:
        try:
            dt = datetime.strptime(genesis, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)
        except ValueError:
            pass

    timestamps: List[int] = []
    for ticker in coin_data.get("tickers", []):
        ts = ticker.get("last_traded_at")
        if not ts:
            continue
        try:
            timestamps.append(int(datetime.fromisoformat(ts.replace("Z", "")).timestamp() * 1000))
        except ValueError:
            continue

    return min(timestamps) if timestamps else None
