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

## Packaging for macOS (PyInstaller)

Use PyInstaller to bundle the CLI into a standalone macOS executable:

1. Install build tooling (preferably in a clean virtual environment):
   ```bash
   python3 -m pip install --upgrade pip
   python3 -m pip install -r requirements.txt pyinstaller
   ```
2. Build the executable (one-file console binary) from the repo root:
   ```bash
   pyinstaller --onefile --name tge-volume-mac --console tge_volume/__main__.py
   ```
   - `--onefile` packs everything into a single binary.
   - `--console` preserves terminal I/O for this CLI.
   - Using the package's `__main__.py` entrypoint matches `python -m tge_volume` while satisfying PyInstaller's required `scriptname` positional argument.
3. Test the output in `dist/`:
   ```bash
   ./dist/tge-volume-mac --help
   ./dist/tge-volume-mac ELIZAOS --output-csv debug_trading_flow.csv
   ```
4. (Optional) Strip debug symbols to reduce size:
   ```bash
   strip dist/tge-volume-mac
   ```
5. Sign and notarize for macOS distribution (requires Apple Developer credentials):
   ```bash
   codesign --deep --force --options runtime --sign "Developer ID Application: Your Name (TEAMID)" dist/tge-volume-mac
   xcrun notarytool submit dist/tge-volume-mac --apple-id <your-apple-id> --team-id <TEAMID> --password <app-password> --wait
   xcrun stapler staple dist/tge-volume-mac
   ```
6. Package for sharing:
   ```bash
   cd dist
   zip tge-volume-mac.zip tge-volume-mac
   ```
   Distribute `tge-volume-mac.zip`; end users can unzip and run from Terminal with the same arguments shown in the Usage examples.
