#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.leah.claude-usage-bar.plist"
TARGET="$HOME/Library/LaunchAgents/$PLIST_NAME"
PYTHON="$(which python3)"

echo "→ Installing Python dependencies"
"$PYTHON" -m pip install --user -r "$APP_DIR/requirements.txt"

echo "→ Rendering launchd plist → $TARGET"
mkdir -p "$HOME/Library/LaunchAgents"
sed -e "s|{{PYTHON}}|$PYTHON|g" \
    -e "s|{{APP_DIR}}|$APP_DIR|g" \
    "$APP_DIR/$PLIST_NAME.template" > "$TARGET"

echo "→ Unloading any existing agent (ignoring errors)"
launchctl unload "$TARGET" 2>/dev/null || true

echo "→ Loading agent"
launchctl load "$TARGET"

echo "✓ Installed. The menu bar icon should appear shortly."
echo "  Logs: $APP_DIR/launchd.{out,err}.log"
echo "  Uninstall with: $APP_DIR/uninstall.sh"
