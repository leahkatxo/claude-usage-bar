#!/usr/bin/env bash
set -euo pipefail

PLIST_NAME="com.leah.claude-usage-bar.plist"
TARGET="$HOME/Library/LaunchAgents/$PLIST_NAME"

if [[ -f "$TARGET" ]]; then
  echo "→ Unloading agent"
  launchctl unload "$TARGET" 2>/dev/null || true
  echo "→ Removing $TARGET"
  rm -f "$TARGET"
  echo "✓ Uninstalled."
else
  echo "No agent installed at $TARGET — nothing to do."
fi
