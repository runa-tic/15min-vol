"""Command line interface entrypoint for the TGE volume analysis tool."""
from __future__ import annotations

from typing import Any, Dict, List

from tabulate import tabulate

from .coingecko import get_coin_tickers, get_expected_tge_ts, search_token
from .exchanges import build_markets, fetch_exchange_stats
from .utils import ts_to_str


def choose_token(matches: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    """Pick a single CoinGecko match when multiple results are returned."""
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]

    print("\nНайдено несколько проектов:")
    for idx, match in enumerate(matches):
        print(f"[{idx}] {match['name']} ({match['symbol']}) — id {match['id']}")

    while True:
        try:
            selected = int(input("Выберите номер: "))
            if 0 <= selected < len(matches):
                return matches[selected]
        except Exception:
            pass
        print("Неверный выбор.")


def _format_results(results: List[Dict[str, Any]]):
    valid = [r for r in results if r["tge_ts"]]
    cex = valid

    print("\n=======================")
    print("   PRICE ACTION / TGE")
    print("=======================\n")

    if valid:
        earliest = min(valid, key=lambda r: r["tge_ts"])
        print("Самый ранний листинг:", earliest["exchange_name"], ts_to_str(earliest["tge_ts"]))

    if cex:
        earliest_cex = min(cex, key=lambda r: r["tge_ts"])
        print("ЯКОРЬ (первый CEX):", earliest_cex["exchange_name"], ts_to_str(earliest_cex["tge_ts"]))
    else:
        print("CEX-листингов не найдено (по данным ccxt).")

    rows = []
    total_cex = 0

    for row in results:
        volume = row["first_15m_volume"] or 0
        total_cex += volume

        rows.append([
            row["exchange_name"],
            ts_to_str(row["tge_ts"]),
            f"{row['first_15m_volume']:.4f}" if row["first_15m_volume"] else "-",
            f"{row['day_open']:.6f}" if row["day_open"] else "-",
            f"{row['day_high']:.6f}" if row["day_high"] else "-",
            f"{row['day_delta_ratio']:.2f}x" if row["day_delta_ratio"] else "-",
            row["error"] or "",
        ])

    print("\nДетализация:\n")
    print(
            tabulate(
                rows,
                headers=[
                    "EXCHANGE",
                    "TGE DATE",
                    "15m VOL",
                    "DAY1 OPEN",
                    "DAY1 HIGH",
                    "HIGH/OPEN",
                "NOTE/ERROR",
            ],
            tablefmt="github",
        )
    )

    print("\nИТОГИ:")
    print("TOTAL_CEX :", total_cex)
    print("TOTAL     :", total_cex)


def main() -> None:
    symbol = input("Введите тикер токена (без $): ").strip()
    matches = search_token(symbol)
    if not matches:
        print("CoinGecko ничего не нашёл.")
        return

    token = choose_token(matches)
    if not token:
        print("Токен не выбран.")
        return

    coin_id = token["id"]
    print(f"\nВыбран токен: {token['name']} ({token['symbol']})")

    tickers, coin_data = get_coin_tickers(coin_id)
    markets = build_markets(tickers)

    print(f"\nНайдено бирж: {len(markets)}")
    for market in markets:
        print(
            f" - {market['exchange_name']} → ccxt_id={market['ccxt_id']} → {market['base']}/{market['quote']}"
        )

    expected_tge_ts = get_expected_tge_ts(coin_data)
    print("\nОжидаемый (оценочный) TGE по данным CoinGecko:", ts_to_str(expected_tge_ts))

    results: List[Dict[str, Any]] = []
    for market in markets:
        print(f"\nОбработка {market['exchange_name']}...")
        if not market["ccxt_id"]:
            results.append(
                {
                    **market,
                    "error": "Биржа не поддерживается ccxt",
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
                expected_tge_ts,
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

    _format_results(results)


if __name__ == "__main__":  # pragma: no cover
    main()
