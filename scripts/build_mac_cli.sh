#!/usr/bin/env bash
# Build the double-clickable macOS CLI package (binary + .command wrapper).
set -euo pipefail

if [[ "${OSTYPE:-}" != darwin* ]]; then
  echo "This script is intended to run on macOS (OSTYPE=darwin*)." >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Installing build dependencies (pip, requirements, pyinstaller)"
if ! python3 -m pip install --upgrade pip; then
  echo "Skipping pip upgrade (likely brew-managed Python); continuing with existing pip." >&2
fi
python3 -m pip install -r requirements.txt pyinstaller

# Clean previous artifacts so we don't ship stale binaries.
rm -rf build dist

echo "==> Building console binary with PyInstaller"
pyinstaller --onefile --name tge-volume-mac --console tge_volume/__main__.py

echo "==> Copying double-click wrapper"
install -m 755 mac_run_cli.command dist/mac_run_cli.command

cat <<'MSG'

Build complete.
You can now double-click dist/mac_run_cli.command in Finder (or run it via Terminal)
to launch the CLI, enter a ticker, and the Terminal window will close automatically after completion.
Artifacts: dist/tge-volume-mac (binary), dist/mac_run_cli.command (double-click launcher)
MSG
