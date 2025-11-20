#!/usr/bin/env bash
# Build the double-clickable macOS CLI package (binary + .command wrapper).
set -euo pipefail

if [[ "${OSTYPE:-}" != darwin* ]]; then
  echo "This script is intended to run on macOS (OSTYPE=darwin*)." >&2
  exit 1
fi

# Resolve repo root
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Clean up any old misplaced .command file
if [[ -f "$REPO_ROOT/mac_run_cli.command" ]]; then
  echo "==> Removing stray root-level mac_run_cli.command"
  rm -f "$REPO_ROOT/mac_run_cli.command"
fi

echo "==> Checking Python + pip source"
PIP_PATH="$(which pip3 || true)"
if [[ "$PIP_PATH" == /opt/homebrew/* ]]; then
  echo "Detected Homebrew-managed pip. Skipping pip self-upgrade."
fi

echo "==> Installing build dependencies (requirements, pyinstaller)"
python3 -m pip install -r requirements.txt pyinstaller

echo "==> Cleaning old build artifacts"
rm -rf build dist

echo "==> Building console binary with PyInstaller"
python3 -m PyInstaller --onefile --name tge-volume-mac --console tge_volume/__main__.py

echo "==> Preparing double-click wrapper"
mkdir -p dist

# Write wrapper directly into dist/
cat > dist/mac_run_cli.command << 'EOF'
#!/bin/bash
# Double-clickable wrapper for macOS that runs the CLI and closes the Terminal window after completion.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN="$SCRIPT_DIR/tge-volume-mac"

if [[ ! -x "$BIN" ]]; then
  echo "Could not find tge-volume-mac binary at: $BIN" >&2
  exit 1
fi

"$BIN" "$@"

osascript -e 'tell application "Terminal" to close front window' >/dev/null 2>&1 || true
EOF

COMMAND_FILE="dist/mac_run_cli.command"

echo "==> Normalizing line endings"
sed -i '' $'s/\r$//' "$COMMAND_FILE"

echo "==> Setting executable permissions"
chmod 755 "$COMMAND_FILE"

echo "==> Removing macOS quarantine flag (Gatekeeper)"
if xattr "$COMMAND_FILE" 2>/dev/null | grep -q "com.apple.quarantine"; then
  xattr -d com.apple.quarantine "$COMMAND_FILE" || true
fi

cat << 'MSG'

===========================================
✅ Build complete!

Double-click here to run the CLI:
    dist/mac_run_cli.command

Artifacts:
  • dist/tge-volume-mac        (binary)
  • dist/mac_run_cli.command   (double-click launcher)

The wrapper + binary now always stay together, and Finder will run it correctly.
===========================================

MSG
