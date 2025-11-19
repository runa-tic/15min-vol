# 15min-vol

A command-line tool that explores token listings and finds the earliest available 15-minute candle (approximate TGE) on `ccxt`-compatible exchanges.

## Project structure

```
.
├── README.md
├── requirements.txt
└── tge_volume/
    ├── __init__.py
    ├── __main__.py
    ├── cli.py
    ├── coingecko.py
    ├── exchanges.py
    └── utils.py
```

- `tge_volume/coingecko.py` — CoinGecko helpers to search tokens and fetch tickers.
- `tge_volume/exchanges.py` — market discovery and ccxt integrations.
- `tge_volume/cli.py` — the CLI that aggregates data and prints the report.

## Installation

Install the dependencies listed in `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Usage

Run the CLI directly from the source tree:

```bash
python -m tge_volume --help
```

Examples:

```bash
# Run interactively (you will be prompted for the ticker)
python -m tge_volume

# Provide the ticker up front and save the 15m trading flow to a custom path
python -m tge_volume ELIZAOS --output-csv debug_trading_flow.csv
```

The app will search CoinGecko for the ticker, gather exchange data, print a consolidated table (with a volume-weighted HIGH/OPEN average), and write the raw 15-minute trading flow to CSV for debugging.
