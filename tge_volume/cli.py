"""Command line interface entrypoint for the TGE volume analysis tool."""
from __future__ import annotations

from typing import Any, Dict, List

import csv
import sys
from argparse import ArgumentParser

from tabulate import tabulate

from .coingecko import get_coin_tickers, search_token
from .exchanges import build_markets, fetch_exchange_stats, fetch_trading_flow
from .utils import shorten_asset, ts_to_str


def choose_token(matches: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    """Pick a single CoinGecko match when multiple results are returned."""
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]

    print("\nMultiple projects found:")
    for idx, match in enumerate(matches):
        print(f"[{idx}] {match['name']} ({match['symbol']}) — id {match['id']}")

    while True:
        try:
            selected = int(input("Choose a number: "))
            if 0 <= selected < len(matches):
                return matches[selected]
        except Exception:
            pass
        print("Invalid selection.")


def _format_results(results: List[Dict[str, Any]]):
    rows = []
    total_volume = 0.0
    weighted_delta_sum = 0.0
    weighted_volume_sum = 0.0

    for row in results:
        volume = row["first_15m_volume"] or 0
        total_volume += volume

        if volume and row.get("day_delta_ratio"):
            weighted_delta_sum += volume * row["day_delta_ratio"]
            weighted_volume_sum += volume

        rows.append([
            row["exchange_name"],
            row.get("ccxt_id") or "-",
            f"{shorten_asset(row['base'])}/{shorten_asset(row['quote'])}",
            ts_to_str(row["tge_ts"]),
            f"{row['first_15m_volume']:.2f}" if row["first_15m_volume"] else "-",
            f"{row['day_open']:.6f}" if row["day_open"] else "-",
            f"{row['day_high']:.6f}" if row["day_high"] else "-",
            f"{row['day_delta_ratio']:.2f}x" if row["day_delta_ratio"] else "-",
            row["error"] or "",
        ])

    print("\nDetails:\n")
    print(
        tabulate(
            rows,
            headers=[
                "EXCHANGE",
                "CCXT ID",
                "PAIR",
                "TGE DATE",
                "15m VOL (USDT)",
                "DAY1 OPEN",
                "DAY1 HIGH",
                "HIGH/OPEN",
                "NOTE/ERROR",
            ],
            tablefmt="github",
        )
    )

    print("\nSUMMARY:")
    print("TOTAL:", f"{total_volume:.2f}")
    weighted_avg = (
        weighted_delta_sum / weighted_volume_sum if weighted_volume_sum else None
    )
    print(
        "AVG HIGH/OPEN (VOL-WEIGHTED):",
        f"{weighted_avg:.2f}x" if weighted_avg else "-",
    )


def _export_trading_flow_csv(markets: List[Dict[str, Any]], path: str) -> None:
    """Dump 15m OHLCV across all available exchanges for debugging."""

    fieldnames = [
        "exchange",
        "symbol",
        "timestamp_ms",
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume_base",
        "volume_quote",
        "error",
    ]

    rows: List[Dict[str, Any]] = []

    for market in markets:
        exchange_name = market["exchange_name"]
        symbol_pair = f"{market['base']}/{market['quote']}"

        if not market["ccxt_id"]:
            rows.append(
                {
                    "exchange": exchange_name,
                    "symbol": symbol_pair,
                    "timestamp_ms": None,
                    "timestamp": None,
                    "open": None,
                    "high": None,
                    "low": None,
                    "close": None,
                    "volume_base": None,
                    "volume_quote": None,
                    "error": market.get("disabled_reason")
                    or "unsupported",
                }
            )
            continue

        try:
            candles = fetch_trading_flow(
                market["ccxt_id"], market["base"], market["quote"], timeframe="15m"
            )
            for candle in candles:
                ts, open_, high, low, close, volume = candle
                volume_quote = volume * close if volume and close else None
                rows.append(
                    {
                        "exchange": exchange_name,
                        "symbol": symbol_pair,
                        "timestamp_ms": ts,
                        "timestamp": ts_to_str(ts),
                        "open": open_,
                        "high": high,
                        "low": low,
                        "close": close,
                        "volume_base": volume,
                        "volume_quote": volume_quote,
                        "error": None,
                    }
                )
        except Exception as exc:
            rows.append(
                {
                    "exchange": exchange_name,
                    "symbol": symbol_pair,
                    "timestamp_ms": None,
                    "timestamp": None,
                    "open": None,
                    "high": None,
                    "low": None,
                    "close": None,
                    "volume_base": None,
                    "volume_quote": None,
                    "error": str(exc),
                }
            )

    if not rows:
        print("\n[DEBUG] Could not collect trading flow — no data available.")
        return

    with open(path, "w", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    rows_written = len(rows)
    error_rows = len([r for r in rows if r["error"]])
    print(
        f"\n[DEBUG] 15m trading flow saved to {path} — "
        f"{rows_written} rows (errors: {error_rows})."
    )


def main(argv: List[str] | None = None) -> None:
    parser = ArgumentParser(description="TGE volume explorer")
    parser.add_argument(
        "symbol",
        nargs="?",
        help="Token ticker symbol (without $)",
    )
    parser.add_argument(
        "--output-csv",
        default="trading_flow_15m.csv",
        help="Path to save the raw 15m trading flow CSV",
    )

    args = parser.parse_args(argv)

    symbol = args.symbol or input("Enter token ticker (without $): ").strip()
    matches = search_token(symbol)
    if not matches:
        print("CoinGecko returned no matches.")
        return

    token = choose_token(matches)
    if not token:
        print("Token not selected.")
        return

    coin_id = token["id"]
    print(f"\nSelected token: {token['name']} ({token['symbol']})")

    tickers, _ = get_coin_tickers(coin_id)
    markets = build_markets(tickers)

    print(f"\nExchanges found: {len(markets)}")

    results: List[Dict[str, Any]] = []
    total = len(markets)
    for idx, market in enumerate(markets, start=1):
        progress = f"[{idx}/{total}] {market['exchange_name']}"
        print(progress, end="\r")
        if not market["ccxt_id"]:
            results.append(
                {
                    **market,
                    "error": market.get("disabled_reason")
                    or "unsupported",
                    "tge_ts": None,
                    "tge_open": None,
                    "first_15m_volume": None,
                    "day_open": None,
                    "day_high": None,
                    "day_delta_ratio": None,
                }
            )
            continue

        try:
            stats = fetch_exchange_stats(
                market["ccxt_id"],
                market["base"],
                market["quote"],
            )
            results.append({**market, **stats, "error": stats.get("note")})
        except Exception as exc:
            results.append(
                {
                    **market,
                    "error": str(exc),
                    "tge_ts": None,
                    "tge_open": None,
                    "first_15m_volume": None,
                    "day_open": None,
                    "day_high": None,
                    "day_delta_ratio": None,
                }
            )
    print(" " * 40, end="\r")
    print()
    _format_results(results)

    # Dump raw 15m trading flow for debugging incorrect TGE selection.
    _export_trading_flow_csv(markets, args.output_csv)


if __name__ == "__main__":  # pragma: no cover
    main(sys.argv[1:])
