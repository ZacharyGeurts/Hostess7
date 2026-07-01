#!/usr/bin/env bash
# Kill Grok Orphans — Linux install (requires root for kill privileges)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VER="$(cat "$ROOT/VERSION" 2>/dev/null | tr -d '\n' || echo unknown)"
PREFIX="${PREFIX:-/usr/local}"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Kill Grok Orphans install requires root to kill orphan processes system-wide."
  echo "Re-run: sudo $0"
  exit 1
fi

echo "Kill Grok Orphans v${VER} — installing…"

if [[ -x "$ROOT/bin/kgo" ]]; then
  install -d "$PREFIX/sbin" /etc/kgo /var/lib/kgo
  install -m 755 "$ROOT/bin/kgo" "$PREFIX/sbin/kgo"
else
  echo "Native kgo binary not found; using Python watchdog."
  install -d "$PREFIX/sbin" /etc/kgo /var/lib/kgo
  install -m 755 "$ROOT/python/kgo_watchdog.py" "$PREFIX/sbin/kgo-watchdog"
fi

install -m 644 "$ROOT/data/kgo-patterns.json" /etc/kgo/kgo-patterns.json

if command -v pip3 >/dev/null 2>&1; then
  pip3 install --break-system-packages -q psutil 2>/dev/null \
    || pip3 install -q psutil 2>/dev/null \
    || true
fi

install -m 644 "$ROOT/packaging/linux/kgo.service" /etc/systemd/system/kgo.service
systemctl daemon-reload
systemctl enable kgo.service
systemctl restart kgo.service

echo ""
echo "Installed. Service: systemctl status kgo"
echo "One-shot scan:     sudo kgo --once --dry-run"
echo "Logs:              journalctl -u kgo -f"