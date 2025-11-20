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

### Double-click wrapper that runs the CLI (no standalone app bundle)

This flow builds the standard console binary and ships a small `.command` helper so macOS users can double-click to run the CLI in Terminal. The Terminal window closes automatically after the CLI finishes.

#### One-command automation (recommended)

On macOS, run the helper script to build the binary, copy the wrapper, and produce the double-clickable launcher in `dist/`:

```bash
./scripts/build_mac_cli.sh
```

After it finishes, double-click `dist/mac_run_cli.command` in Finder (or run `./dist/mac_run_cli.command` in Terminal), enter your ticker when prompted, and the Terminal window will auto-close when the CLI completes.

#### Manual steps

1. Install build tooling (preferably in a clean virtual environment):
   ```bash
   python3 -m pip install --upgrade pip || echo "(Skipping pip upgrade; brew-managed Python may block uninstall)"
   python3 -m pip install -r requirements.txt pyinstaller
   ```
2. Build the console executable from the repo root:
   ```bash
   pyinstaller --onefile --name tge-volume-mac --console tge_volume/__main__.py
   ```
   - `--onefile` packs everything into a single binary.
   - `--console` preserves terminal I/O for this CLI.
   - Using the package's `__main__.py` entrypoint matches `python -m tge_volume` while satisfying PyInstaller's required `scriptname` positional argument.
3. Copy the double-click wrapper into the build output and make it executable:
   ```bash
   install -m 755 mac_run_cli.command dist/mac_run_cli.command
   ```
   - The wrapper expects `tge-volume-mac` to live next to it inside `dist/`.
   - If Finder still reports a permissions warning (e.g., after copying between drives), run `chmod +x dist/mac_run_cli.command` once to restore the execute bit.
4. Test locally:
   ```bash
   ./dist/mac_run_cli.command --help
   ./dist/mac_run_cli.command ELIZAOS --output-csv debug_trading_flow.csv
   ```
   - Double-click `mac_run_cli.command` in Finder to launch the CLI; the Terminal window will auto-close when execution ends.
5. (Optional) Strip debug symbols to reduce size:
   ```bash
   strip dist/tge-volume-mac
   ```
6. Sign and notarize for macOS distribution (requires Apple Developer credentials):
   ```bash
   codesign --deep --force --options runtime --sign "Developer ID Application: Your Name (TEAMID)" dist/tge-volume-mac dist/mac_run_cli.command
   xcrun notarytool submit dist/tge-volume-mac dist/mac_run_cli.command --apple-id <your-apple-id> --team-id <TEAMID> --password <app-password> --wait
   xcrun stapler staple dist/tge-volume-mac dist/mac_run_cli.command
   ```
7. Package for sharing:
   ```bash
   cd dist
   zip tge-volume-mac.zip tge-volume-mac mac_run_cli.command
   ```
   Distribute `tge-volume-mac.zip`; end users can unzip and double-click `mac_run_cli.command` to run the CLI without keeping Terminal open afterwards.
