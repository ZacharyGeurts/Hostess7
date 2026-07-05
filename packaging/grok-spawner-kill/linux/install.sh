#!/usr/bin/env bash
# Install field-grok-spawner-kill systemd service (sudo mememe).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
PW="${HOSTESS7_SUDO_PW:-mememe}"
UNIT_NAME="field-grok-spawner-kill.service"
UNIT_DST="/etc/systemd/system/${UNIT_NAME}"
STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
PY="${PYTHON:-python3}"

log() { printf '[grok-spawner-kill] %s\n' "$*"; }

if ! echo "$PW" | sudo -S -v 2>/dev/null; then
  log "ERROR: sudo password required — set HOSTESS7_SUDO_PW or use mememe"
  exit 1
fi

log "install instakill service from ${ROOT}"
chmod +x "${ROOT}/lib/field-grok-spawner-kill.py"

UNIT_BODY="$(sed \
  -e "s|NEXUS_INSTALL_ROOT|${ROOT}|g" \
  -e "s|NEXUS_STATE_DIR|${STATE_DIR}|g" \
  "${ROOT}/packaging/grok-spawner-kill/linux/field-grok-spawner-kill.service")"

echo "$UNIT_BODY" | sudo tee "$UNIT_DST" >/dev/null
sudo mkdir -p "$STATE_DIR"
sudo chown -R "$(id -un):$(id -gn)" "$STATE_DIR" 2>/dev/null || true

sudo systemctl daemon-reload
sudo systemctl enable "$UNIT_NAME"
sudo systemctl reset-failed "$UNIT_NAME" 2>/dev/null || true
sudo systemctl restart "$UNIT_NAME"

sleep 1
if systemctl is-active --quiet "$UNIT_NAME"; then
  log "active — journalctl -u ${UNIT_NAME} -f"
else
  log "WARN: service not active — journalctl -u ${UNIT_NAME} -n 30"
  exit 1
fi

log "one-shot: ${PY} ${ROOT}/lib/field-grok-spawner-kill.py instakill"