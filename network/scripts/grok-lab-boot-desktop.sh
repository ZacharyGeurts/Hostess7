#!/usr/bin/env bash
# AmmoLang subfolder route — AML_BUILD=1 (default)
_aml_find_root() {
  local d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  while [[ "$d" != "/" ]]; do
    [[ -f "$d/lib/ammolang-run.sh" ]] && echo "$d" && return 0
    d="$(dirname "$d")"
  done
  return 1
}
if [[ "${AML_BUILD:-1}" != "0" ]]; then
  _AML_ROOT="$(_aml_find_root 2>/dev/null || true)"
  if [[ -n "$_AML_ROOT" ]]; then
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" grok_lab_boot "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

# Grok AI Lab — bootable AmmoOS desktop install + boot protection.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NL="${NEXUS_INSTALL_ROOT:-$(cd "$ROOT/.." && pwd)}"
SG="${SG_ROOT:-$(cd "$NL/.." && pwd)}"
STATE="${NEXUS_STATE_DIR:-$NL/.nexus-state}"
PY="${GROK_LAB_PY:-python3}"
PANEL_PORT="${NEXUS_THREAT_PANEL_PORT:-9477}"

export NEXUS_INSTALL_ROOT="$NL"
export KILROY_ROOT="${KILROY_ROOT:-$NL/KILROY}"
export GROK_LAB_ROOT="$ROOT"
export GROK_LAB_STATE="${GROK_LAB_STATE:-$ROOT/.lab-state}"
export NEXUS_STATE_DIR="$STATE"
export SG_ROOT="$SG"
export NEXUS_BOOT_REKILL=1
export NEXUS_BOOT_REKILL_ONLINE="${NEXUS_BOOT_REKILL_ONLINE:-0}"
export NEXUS_EVERY_KILL_REKILL=1
export ZOCR_REKILL_AT_BOOT=1

log() { printf '[grok-lab-desktop] %s\n' "$*"; }

mkdir -p "$GROK_LAB_STATE" "$STATE"

log "=== Grok AI Lab bootable AmmoOS desktop ==="
log "home=127.0.0.1 desktop=http://127.0.0.1:${PANEL_PORT}/grok-lab"

# Boot protection + Final Eye
"$PY" "$NL/lib/grok-ai-lab.py" boot
"$PY" "$NL/lib/grok-ai-lab.py" start 2>/dev/null || true

# Host desktop launcher (AmmoOS icon)
if [[ -f "$NL/lib/nexus-host-desktop-install.sh" ]]; then
  # shellcheck source=/dev/null
  source "$NL/lib/nexus-host-desktop-install.sh" 2>/dev/null || true
  declare -f nexus_host_desktop_install >/dev/null 2>&1 && \
    nexus_host_desktop_install 2>/dev/null || true
fi

# systemd unit (optional — grandma-safe Mint pattern)
UNIT=/etc/systemd/system/grok-lab.service
if command -v systemctl >/dev/null 2>&1 && [[ "$(id -u)" -eq 0 || "${GROK_LAB_INSTALL_SYSTEMD:-0}" == "1" ]]; then
  install -d -m 0755 /etc/systemd/system 2>/dev/null || true
  cat >"$UNIT" <<EOF
[Unit]
Description=Grok AI Lab — Final Eye OCR brain + boot RE-KILL
After=network.target nexus-genius.service
Wants=nexus-genius.service

[Service]
Type=oneshot
RemainAfterExit=yes
Environment=NEXUS_INSTALL_ROOT=$NL
Environment=NEXUS_STATE_DIR=$STATE
Environment=GROK_LAB_ROOT=$ROOT
Environment=NEXUS_BOOT_REKILL=1
Environment=ZOCR_REKILL_AT_BOOT=1
ExecStart=$NL/GrokLab/scripts/grok-lab-run.sh boot
ExecStartPost=$NL/GrokLab/scripts/grok-lab-run.sh start
WorkingDirectory=$NL

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload 2>/dev/null || true
  systemctl enable grok-lab.service 2>/dev/null || true
  log "systemd grok-lab.service enabled"
fi

# Desktop entry (opens AmmoOS Grok Lab surface)
DESKTOP_DIR="${HOME:-/home/default}/.local/share/applications"
mkdir -p "$DESKTOP_DIR"
cat >"$DESKTOP_DIR/grok-ai-lab.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Grok AI Lab
Comment=AmmoOS — Final Eye OCR brain, RE-KILL at boot
Exec=xdg-open http://127.0.0.1:${PANEL_PORT}/grok-lab
Icon=$NL/Queen/world/assets/icons/prog-eyeball-48.png
Terminal=false
Categories=System;Security;
StartupNotify=true
EOF
chmod 644 "$DESKTOP_DIR/grok-ai-lab.desktop" 2>/dev/null || true

# Boot marker
"$PY" - <<PY
import json, os
from datetime import datetime, timezone
from pathlib import Path
doc = {
    "schema": "grok-lab-boot-desktop/v1",
    "ok": True,
    "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "desktop_url": f"http://127.0.0.1:{os.environ.get('NEXUS_THREAT_PANEL_PORT', '9477')}/grok-lab",
    "field_url": f"http://127.0.0.1:{os.environ.get('NEXUS_THREAT_PANEL_PORT', '9477')}/field",
    "cli": str(Path(os.environ['GROK_LAB_ROOT']) / 'scripts' / 'grok-lab-run.sh'),
}
Path(os.environ['NEXUS_STATE_DIR']).mkdir(parents=True, exist_ok=True)
Path(os.environ['NEXUS_STATE_DIR'], 'grok-lab-boot-desktop.json').write_text(
    json.dumps(doc, indent=2) + "\\n", encoding="utf-8"
)
print(json.dumps(doc, indent=2))
PY

log "Desktop: http://127.0.0.1:${PANEL_PORT}/grok-lab"
log "AmmoOS:  http://127.0.0.1:${PANEL_PORT}/field  → Grok AI Lab icon"
log "CLI:     bash GrokLab/scripts/grok-lab-run.sh battery"
