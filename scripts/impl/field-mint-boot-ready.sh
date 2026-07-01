# AmmoLang boundary route — AML_BUILD=1 universal boundary
_aml_find_root() {
  local d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  while [[ "$d" != "/" ]]; do
    [[ -f "$d/lib/ammolang-run.sh" ]] && echo "$d" && return 0
    d="$(dirname "$d")"
  done
  return 1
}
if [[ "${AML_BUILD:-1}" != "0" ]] && [[ -z "${AML_BOUNDARY_ACTIVE:-}" ]]; then
  _AML_ROOT="$(_aml_find_root 2>/dev/null || true)"
  if [[ -n "$_AML_ROOT" ]]; then
    export AML_BOUNDARY_ACTIVE=1
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/impl/field-mint-boot-ready.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Grandma-safe Mint boot — non-destructive: normal GRUB/login, field layer on demand (F9).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export NEXUS_INSTALL_ROOT="${ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-field-drive/nexus-field/state}"
export SG_ROOT="$(cd "${ROOT}/.." && pwd)"
export PATH="${ROOT}/PythonG/bin:${PATH}"
export DISPLAY="${DISPLAY:-:0}"

PY="${ROOT}/Grok16/python/driver/gpy16_driver.py"
HOME_DIR="${HOME:-/home/default}"
AUTOSTART="${HOME_DIR}/.config/autostart"

mkdir -p "${NEXUS_STATE_DIR}" "${AUTOSTART}"

field_mint_sudo_ready() {
  [[ "$(id -u)" -eq 0 ]] && return 0
  if sudo -n true 2>/dev/null; then
    return 0
  fi
  if [[ ! -t 0 ]]; then
    echo "Skipped: nexus-genius.service needs sudo (no cached credentials)." >&2
    echo "  Run: sudo ./lib/ammolang-run.sh exec script:scripts/impl/field-mint-boot-ready.sh" >&2
    return 1
  fi
  echo "Administrator access needed to install nexus-genius.service." >&2
  echo "Enter your password when prompted (Ctrl+C skips this step)." >&2
  if sudo -v; then
    return 0
  fi
  echo "Skipped: nexus-genius.service (sudo declined or unavailable)." >&2
  return 1
}

echo "=== Field / defield (host mirror only — GRUB untouched) ==="
pythong "${ROOT}/lib/field-non-fielded-safety.py" purge-nested-drive --apply 2>/dev/null || true
pythong "${ROOT}/lib/field-non-fielded-safety.py" audit | grep -q '"defield_ok": true' || {
  echo "WARN: defield audit not clean — fix tails before fielding physical drive" >&2
}

pythong "${ROOT}/lib/field-drive-system.py" publish 2>/dev/null | grep -q '"ok": true' && \
  echo "  Field mirror published (.nexus-field-drive)" || \
  echo "  WARN: field publish incomplete" >&2

echo "=== Login autostart (F9 + tray + ZNetwork — no fullscreen hijack) ==="
pythong "${ROOT}/lib/field-underlay-hotkey.py" install 2>/dev/null || true
# shellcheck source=/dev/null
[[ -f "${ROOT}/lib/panel-tray.sh" ]] && source "${ROOT}/lib/panel-tray.sh"
declare -f nexus_panel_tray_install_autostart >/dev/null 2>&1 && \
  nexus_panel_tray_install_autostart 2>/dev/null || true
# shellcheck source=/dev/null
[[ -f "${ROOT}/lib/znetwork-field.sh" ]] && source "${ROOT}/lib/znetwork-field.sh"
declare -f nexus_znetwork_install_autostart >/dev/null 2>&1 && \
  nexus_znetwork_install_autostart 2>/dev/null || true

echo "=== Stack posture (no reboot) ==="
curl -sf "http://127.0.0.1:9477/field" >/dev/null 2>&1 && echo "  Panel :9477 up" || echo "  Panel down — run: ./lib/ammolang-run.sh exec script:scripts/start-field-stack.sh"
curl -sf "http://127.0.0.1:9481/api/status" >/dev/null 2>&1 && echo "  Queen :9481 up" || echo "  Queen down"

echo "=== Early boot dry-run (ZNetwork + C2 before guest OS — no reboot) ==="
if bash "${ROOT}/scripts/nexus-field-early-boot.sh" 2>/dev/null; then
  if [[ -f "${NEXUS_STATE_DIR}/field-underlay-early.json" ]]; then
    echo "  Early layer OK — $(grep -o '"znetwork_active":[^,]*' "${NEXUS_STATE_DIR}/field-underlay-early.json" 2>/dev/null || echo znetwork) $(grep -o '"nexus_c2_panel":[^,]*' "${NEXUS_STATE_DIR}/field-underlay-early.json" 2>/dev/null || echo c2)"
  else
    echo "  Early boot ran (marker pending)"
  fi
else
  echo "  WARN: early boot dry-run incomplete" >&2
fi

echo "=== systemd (early layer before desktop, genius after — GRUB untouched) ==="
NL="$(cd "${ROOT}" && pwd)"
SG="$(cd "${ROOT}/.." && pwd)"
H7="${ROOT}/Hostess7"
EARLY_UNIT=/etc/systemd/system/nexus-field-early.service
GENIUS_UNIT=/etc/systemd/system/nexus-genius.service
if command -v systemctl >/dev/null 2>&1 && field_mint_sudo_ready; then
  sudo tee "$EARLY_UNIT" >/dev/null <<EARLYEOF
[Unit]
Description=NEXUS Field Early — ZNetwork + C2 before guest OS login
DefaultDependencies=no
After=network-online.target
Before=display-manager.service lightdm.service gdm.service sddm.service
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=oneshot
RemainAfterExit=yes
User=default
Environment=HOME=/home/default
Environment=USER=default
Environment=NEXUS_INSTALL_ROOT=${NL}
Environment=NEXUS_STATE_DIR=${NEXUS_STATE_DIR}
Environment=SG_ROOT=${SG}
Environment=NEXUS_ZNETWORK_NO_SUDO=1
Environment=PATH=${ROOT}/PythonG/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=${NL}/scripts/nexus-field-early-boot.sh
TimeoutStartSec=180

[Install]
WantedBy=multi-user.target
EARLYEOF
  sudo tee "$GENIUS_UNIT" >/dev/null <<GENIUSEOF
[Unit]
Description=NEXUS-Shield Genius Layer (NewLatest checkout)
After=network-online.target nexus-field-early.service
Wants=nexus-field-early.service
StartLimitIntervalSec=300
StartLimitBurst=5

[Service]
Type=simple
User=default
Environment=HOME=/home/default
Environment=USER=default
Environment=NEXUS_INSTALL_ROOT=${NL}
Environment=NEXUS_STATE_DIR=${NEXUS_STATE_DIR}
Environment=SG_ROOT=${SG}
Environment=PATH=${ROOT}/PythonG/bin:/usr/local/bin:/usr/bin:/bin
Environment=NEXUS_TRAINING_VIEWER_BOOT=0
Environment=ZNETWORK_FAST=1
ExecStart=${NL}/lib/nexus-daemon.sh
TimeoutStartSec=120
ExecStop=/bin/bash -c 'pkill -f threat-panel-http.py 2>/dev/null; pkill -P \$MAINPID 2>/dev/null; exit 0'
KillMode=mixed
Restart=on-failure
RestartSec=10
Nice=19
IOSchedulingClass=idle
CPUQuota=5%
MemoryMax=256M
ReadWritePaths=${NL}/.nexus-field-drive ${NL}/.nexus-state /var/lib/nexus-shield /var/log/nexus-alerts.log
BindReadOnlyPaths=-${H7}
BindPaths=/var/lib/nexus-shield/hostess7-cache:${H7}/cache
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_RAW CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_RAW CAP_NET_BIND_SERVICE CAP_DAC_OVERRIDE CAP_SETGID CAP_SETUID CAP_SYS_ADMIN
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
GENIUSEOF
  sudo systemctl daemon-reload 2>/dev/null || true
  sudo systemctl reset-failed nexus-field-early.service nexus-genius.service 2>/dev/null || true
  sudo systemctl enable nexus-field-early.service nexus-genius.service 2>/dev/null || true
  sudo chown -R "$(id -un):$(id -gn)" "${NL}/.nexus-field-drive" 2>/dev/null || true
  chmod +x "${NL}/lib/nexus-daemon.sh" "${NL}/scripts/nexus-field-early-boot.sh" \
    "${NL}/scripts/impl/field-mint-boot-ready.sh" "${NL}/scripts/impl/field-mint-pre-reboot-test.sh" \
    "${NL}/lib/ammolang-run.sh" 2>/dev/null || true
  sudo systemctl restart nexus-field-early.service 2>/dev/null || true
  sudo systemctl restart nexus-genius.service 2>/dev/null || true
  sleep 2
  if systemctl is-active --quiet nexus-field-early.service 2>/dev/null; then
    echo "  nexus-field-early.service active (ZNetwork + C2 before desktop)"
  else
    echo "  WARN: nexus-field-early not active — journalctl -u nexus-field-early -n 20" >&2
  fi
  if systemctl is-active --quiet nexus-genius.service 2>/dev/null; then
    echo "  nexus-genius.service active (NewLatest)"
  else
    echo "  WARN: nexus-genius not active — journalctl -u nexus-genius -n 20" >&2
  fi
fi

echo "=== Ready ==="
echo "  Reboot → GRUB/Mint/Windows unchanged; early layer loads before login desktop"
echo "  Boot order: KILROY → unified field (drives/RAM/board/voltage/FCC) → ZNetwork → C2 → guest OS"
echo "  After login → press F9 for full KILROY + AmmoOS stack"
echo "  Underlay: passthrough (not committed — host stays boss)"
echo "  Field mirror: ${ROOT}/.nexus-field-drive"
