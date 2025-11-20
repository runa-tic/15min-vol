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
