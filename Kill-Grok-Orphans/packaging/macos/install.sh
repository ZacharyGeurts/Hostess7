#!/usr/bin/env bash
# Kill Grok Orphans — macOS install (requires admin for kill privileges)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VER="$(cat "$ROOT/VERSION" 2>/dev/null | tr -d '\n' || echo unknown)"
PREFIX="${PREFIX:-/usr/local}"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "macOS install requires admin (sudo) to kill orphan processes."
  echo "Re-run: sudo $0"
  exit 1
fi

echo "Kill Grok Orphans v${VER} — installing…"

install -d "$PREFIX/sbin" /etc/kgo /var/lib/kgo
install -m 755 "$ROOT/python/kgo_watchdog.py" "$PREFIX/sbin/kgo-watchdog"
install -m 644 "$ROOT/data/kgo-patterns.json" /etc/kgo/kgo-patterns.json

pip3 install psutil 2>/dev/null || python3 -m pip install psutil

PLIST=/Library/LaunchDaemons/com.grok.killorphans.plist
install -m 644 "$ROOT/packaging/macos/com.grok.killorphans.plist" "$PLIST"
launchctl bootout system/com.grok.killorphans 2>/dev/null || true
launchctl bootstrap system "$PLIST"
launchctl enable system/com.grok.killorphans

echo ""
echo "Installed. Check: sudo launchctl print system/com.grok.killorphans"
echo "One-shot:         sudo kgo-watchdog --once --dry-run -c /etc/kgo/kgo-patterns.json"