#!/usr/bin/env bash
# Build the double-clickable macOS CLI package (binary + .command wrapper + .app bundle)
set -euo pipefail

if [[ "${OSTYPE:-}" != darwin* ]]; then
  echo "This script is intended to run on macOS (OSTYPE=darwin*)." >&2
  exit 1
fi

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Checking Python environment"
PIP_PATH="$(which pip3 || true)"
if [[ "$PIP_PATH" == /opt/homebrew/* ]]; then
  echo "Detected Homebrew-managed pip. Skipping pip self-upgrade."
fi

echo "==> Installing build dependencies"
python3 -m pip install -r requirements.txt pyinstaller

echo "==> Cleaning previous build artifacts"
rm -rf build dist
mkdir dist

echo "==> Building PyInstaller CLI binary"
python3 -m PyInstaller --onefile --name tge-volume-mac --console tge_volume/__main__.py

################################################################################
# 1. Write the .command double-click wrapper (still useful for dev)
################################################################################

echo "==> Creating mac_run_cli.command"
cat > dist/mac_run_cli.command << 'EOF'
#!/bin/bash
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

chmod 755 dist/mac_run_cli.command
sed -i '' $'s/\r$//' dist/mac_run_cli.command || true
xattr -d com.apple.quarantine dist/mac_run_cli.command 2>/dev/null || true


################################################################################
# 2. Build the macOS .app bundle
################################################################################

APP_NAME="tge-volume.app"
APP_DIR="dist/$APP_NAME"

echo "==> Creating .app bundle at $APP_DIR"

# Clean & create structure
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"

# Copy the binary into Resources/
cp dist/tge-volume-mac "$APP_DIR/Contents/Resources/"

# Create the launcher executable inside Contents/MacOS
cat > "$APP_DIR/Contents/MacOS/tge-volume-cli" << 'EOF'
#!/bin/bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$APP_DIR/Resources/tge-volume-mac"

if [[ ! -x "$BIN" ]]; then
  echo "Error: CLI binary not found at $BIN" >&2
  exit 1
fi

osascript <<OSASCRIPT
tell application "Terminal"
  activate
  do script " '$BIN'; exit"
end tell
OSASCRIPT
EOF

chmod 755 "$APP_DIR/Contents/MacOS/tge-volume-cli"

# Write Info.plist
cat > "$APP_DIR/Contents/Info.plist" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>tge-volume</string>

  <key>CFBundleExecutable</key>
  <string>tge-volume-cli</string>

  <key>CFBundleIdentifier</key>
  <string>com.yourdomain.tge-volume</string>

  <key>CFBundleVersion</key>
  <string>1.0</string>

  <key>CFBundlePackageType</key>
  <string>APPL</string>

  <key>LSMinimumSystemVersion</key>
  <string>10.13</string>
</dict>
</plist>
EOF

# Remove any quarantine flags for Gatekeeper
xattr -dr com.apple.quarantine "$APP_DIR" 2>/dev/null || true

echo ""
echo "=========================================="
echo "✅ Build complete!"
echo "Artifacts created in dist/:"
echo "  • tge-volume-mac          (PyInstaller binary)"
echo "  • mac_run_cli.command     (developer double-click wrapper)"
echo "  • tge-volume.app          (REAL macOS app bundle)"
echo "=========================================="
echo ""
