#!/bin/bash
# Double-clickable wrapper for macOS that runs the CLI and closes the Terminal window after completion.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN="$SCRIPT_DIR/tge-volume-mac"

if [[ ! -x "$BIN" ]]; then
  echo "Expected CLI binary at: $BIN" >&2
  exit 1
fi

"$BIN" "$@"

# Close the Terminal window that was opened for this script (ignore errors if Terminal is not available)
osascript -e 'tell application "Terminal" to close front window' >/dev/null 2>&1 || true
