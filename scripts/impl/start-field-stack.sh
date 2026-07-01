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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/impl/start-field-stack.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash

# Unified field stack — NewLatest NEXUS + Queen World + Final_Eye 1.1
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SG="$(cd "${ROOT}/.." && pwd)"
QUEEN="${QUEEN_ROOT:-${ROOT}/Queen}"
FINAL_EYE="${FINAL_EYE_ROOT:-${ROOT}/Final_Eye}"
FINAL_EAR="${FINAL_EAR_ROOT:-${ROOT}/Final_Ear}"
WORLD_REDATA="${WORLD_REDATA_ROOT:-${SG}/World_Redata}"
_state_explicit=0
[[ -n "${NEXUS_STATE_DIR:-}" ]] && _state_explicit=1
_state_saved="${NEXUS_STATE_DIR:-}"
# shellcheck source=/dev/null
source "${ROOT}/lib/nexus-common.sh"
export NEXUS_INSTALL_ROOT="${ROOT}"
export NEXUS_FIELD_STANDALONE=1
nexus_init_runtime_paths
if [[ "$_state_explicit" -eq 1 ]]; then
  export NEXUS_STATE_DIR="$_state_saved"
fi
unset _state_explicit _state_saved
STATE="${NEXUS_STATE_DIR}"

PY="${QUEEN}/scripts/queen-py"
PANEL_PORT="${NEXUS_THREAT_PANEL_PORT:-9477}"
EYE_PORT="${FINAL_EYE_PORT:-9479}"
WORLD_PORT="${QUEEN_WORLD_PORT:-9481}"

export SG_ROOT="${SG}"
export TDIR="${TDIR:-${HOME}/.grok/projects/home-default-Desktop-SG/terminals}"
export NEXUS_FIELD_STANDALONE=1
export QUEEN_ROOT="${QUEEN}"
export FINAL_EYE_ROOT="${FINAL_EYE}"
export FINAL_EAR_ROOT="${FINAL_EAR}"
export WORLD_REDATA_ROOT="${WORLD_REDATA}"
export HOSTESS7_ROOT="${HOSTESS7_ROOT:-${NEXUS_INSTALL_ROOT:-${SG}/NewLatest}/Hostess7}"
# shellcheck source=/dev/null
source "${ROOT}/lib/sg-paths.sh"
sg_paths_export_defaults

export KILROY_PC_CORE=1
export KILROY_ZNETWORK_ABSORBED=1
export AMMOOS_INSIDE_QUEEN=0
export QUEEN_STANDALONE_BROWSER=1
export AMMOOS_DESKTOP_RTX=AMOURANTHRTX
export NEXUS_FIELD_BROWSER_QUEEN=1
export HOSTESS7_ANGEL_MANDATE=1
export NEXUS_HOSTESS7_INTERNET=1
export HOSTESS7_INTERNET=1
export FINAL_EYE_ASSIST=1
export QUEEN_BROWSER_STRIPPED="${QUEEN_BROWSER_STRIPPED:-1}"
export QUEEN_BOOT_OS="${QUEEN_BOOT_OS:-0}"
export QUEEN_BROWSER_HOME="${QUEEN_BROWSER_HOME:-http://127.0.0.1:9481/world/kilroy-home.html}"
export QUEEN_BROWSER_START="${QUEEN_BROWSER_START:-$QUEEN_BROWSER_HOME}"
export QUEEN_WEB_SHELL="${QUEEN_WEB_SHELL:-1}"
export QUEEN_SKIP_RTX_BOOT="${QUEEN_SKIP_RTX_BOOT:-1}"
export NEXUS_EMBED_PANEL_IN_ENGINE=0
export NEXUS_BOOT_C2_ONLY="${NEXUS_BOOT_C2_ONLY:-1}"
export NEXUS_QUEEN_LAYER_AUTOSTART=0
export NEXUS_C2_DESKTOP_LAUNCH="${NEXUS_C2_DESKTOP_LAUNCH:-0}"
export NEXUS_C2_KIOSK="${NEXUS_C2_KIOSK:-0}"
export NEXUS_FIELD_LAUNCH_BROWSER="${NEXUS_FIELD_LAUNCH_BROWSER:-0}"
export NEXUS_AUTO_LAUNCH_QUEEN_BROWSER="${NEXUS_AUTO_LAUNCH_QUEEN_BROWSER:-0}"
export AMMOOS_WINDOW_MODE="${AMMOOS_WINDOW_MODE:-1}"
export AMMOOS_DESKTOP_URL="http://127.0.0.1:${PANEL_PORT}/field"
export NEXUS_C2_LAUNCH_URL="http://127.0.0.1:${PANEL_PORT}/field"
export AMMOOS_SHOW_DESKTOP_ICONS=1

mkdir -p "${STATE}"

# EXTREME host tier — enable offensive defenses (autokill, re-kill, paranoia, Hell Kit).
# shellcheck source=/dev/null
source "${ROOT}/lib/nexus-settings.sh"
if grep -q '"security_level": "extreme"' "${ROOT}/state/host-security-tier.json" 2>/dev/null; then
  nexus_settings_apply_extreme_defaults || true
else
  nexus_host_extreme_apply_if_eligible || nexus_settings_apply_consumer_defaults || true
fi
if [[ "$(nexus_settings_get NEXUS_PARANOIA_MODE)" == "1" ]]; then
  "${PY:-python3}" "${ROOT}/lib/field-toolkit-db.py" toggle paranoia_mode on >/dev/null 2>&1 || true
fi

# Legacy Latest/NEXUS-Shield panel (often root-owned) blocks :9477 until stopped.
if pgrep -f '/Latest/NEXUS-Shield/lib/threat-panel-http.py' >/dev/null 2>&1; then
  echo "WARN: Legacy NEXUS-Shield panel holds :9477 — stopping for NewLatest field stack…" >&2
  if command -v sudo >/dev/null 2>&1; then
    sudo pkill -f '/Latest/NEXUS-Shield/lib/threat-panel-http.py' 2>/dev/null || true
    sleep 1
  fi
  if pgrep -f '/Latest/NEXUS-Shield/lib/threat-panel-http.py' >/dev/null 2>&1; then
    export NEXUS_THREAT_PANEL_PORT=9478
    PANEL_PORT=9478
    echo "WARN: Could not free :9477 — NewLatest panel will use :9478" >&2
  fi
fi

echo "=== NewLatest field stack (KILROY → AmmoOS → Queen) ==="
echo "  KILROY core ZNetwork absorbed — ./scripts/kilroy-load-os.sh for desktop"
echo "  NEXUS panel :${PANEL_PORT}"
echo "  Final_Eye   :${EYE_PORT}"
echo "  Queen World :${WORLD_PORT} (standalone browser)"
echo "  ZNEWOCR     ${ZNEWOCR:-retired — Final_Eye only}"
echo "  World_Redata ${WORLD_REDATA}"
echo "  Install     ${ROOT}"
echo ""

# KILROY PC core — boards network lane (ZNetwork absorbed) before stack services.
if [[ -f "${ROOT}/lib/kilroy-core.sh" ]]; then
  # shellcheck source=/dev/null
  source "${ROOT}/lib/kilroy-core.sh"
  nexus_kilroy_core_board 2>/dev/null || true
fi

# Vestigial cleanup + network lane impl (ex-ZNetwork, owned by KILROY core).
if [[ -f "${ROOT}/lib/nexus-vestigial-cleanup.sh" ]]; then
  # shellcheck source=/dev/null
  source "${ROOT}/lib/nexus-vestigial-cleanup.sh"
  nexus_vestigial_cleanup_run 2>/dev/null || true
fi
# shellcheck source=/dev/null
[[ -f "${ROOT}/lib/nexus-field-os.sh" ]] && source "${ROOT}/lib/nexus-field-os.sh"
declare -f nexus_field_os_install_host_desktop >/dev/null 2>&1 && \
  nexus_field_os_install_host_desktop 2>/dev/null || true
if [[ -x "${ROOT}/scripts/integrate-znetwork.sh" ]]; then
  ZNETWORK_INTEGRATE_SKIP_BATTERY="${ZNETWORK_INTEGRATE_SKIP_BATTERY:-1}" \
    bash "${ROOT}/scripts/integrate-znetwork.sh" || true
fi
if [[ -f "${STATE}/znetwork-integrated.env" ]]; then
  # shellcheck source=/dev/null
  source "${STATE}/znetwork-integrated.env"
fi
# shellcheck source=/dev/null
source "${ROOT}/lib/znetwork-field.sh"
export NEXUS_ZNETWORK="${NEXUS_ZNETWORK:-1}"
export NEXUS_ZNETWORK_PROMPT=0
nexus_znetwork_startup_with_us 2>/dev/null || nexus_znetwork_publish 2>/dev/null || true

# AmmoCode Stack — lean editor on :9555 (G16 run/compile, 243 filetypes)
AMMOCODE_PORT="${AMMOCODE_PORT:-9555}"
export AMMOCODE_ROOT="${AMMOCODE_ROOT:-${SG}/AmmoCode}"
if [[ -f "${STATE}/ammocode-integrated.env" ]]; then
  # shellcheck source=/dev/null
  source "${STATE}/ammocode-integrated.env"
fi
if ! curl -sf "http://127.0.0.1:${AMMOCODE_PORT}/api/ammocode" \
  -X POST -H 'Content-Type: application/json' -d '{"action":"ping"}' >/dev/null 2>&1; then
  if [[ -f "${AMMOCODE_ROOT}/ammocode.py" ]]; then
    (cd "${AMMOCODE_ROOT}" && nohup python3 ammocode.py >>"${STATE}/ammocode-http.log" 2>&1 &)
    for _ in $(seq 1 12); do
      curl -sf "http://127.0.0.1:${AMMOCODE_PORT}/api/ammocode" \
        -X POST -H 'Content-Type: application/json' -d '{"action":"ping"}' >/dev/null 2>&1 && break
      sleep 0.25
    done
  fi
fi

echo "=== Grok AI Lab (bootable desktop) ==="
if [[ -x "${ROOT}/GrokLab/scripts/grok-lab-boot-desktop.sh" ]]; then
  GROK_LAB_INSTALL_SYSTEMD=0 NEXUS_BOOT_REKILL_ONLINE=0 \
    bash "${ROOT}/GrokLab/scripts/grok-lab-boot-desktop.sh" 2>/dev/null | tail -8 || true
else
  "${PY:-python3}" "${ROOT}/lib/grok-ai-lab.py" boot 2>/dev/null || true
fi

echo "=== Field 1 hostile scan (not Field 1 → hostile → bring) ==="
if [[ -f "${ROOT}/GrokLab/deploy/field-one-world-bring.sh" ]]; then
  export GROK_LAB_NODE_REGION=local GROK_LAB_NODE_ID=node-local
  bash "${ROOT}/GrokLab/deploy/field-one-world-bring.sh" 2>/dev/null | tail -4 || true
fi

echo "=== sense package meld ==="
"${PY}" "${ROOT}/lib/field-sense-package-meld.py" meld 2>/dev/null || true

export NEXUS_ZNETWORK="${NEXUS_ZNETWORK:-1}"
export NEXUS_ZNETWORK_PROMPT=0
export NEXUS_ZNETWORK_NO_SUDO=1

NEXUS_BOOT_IMPL="${NEXUS_BOOT_IMPL:-0}" NEXUS_ZNETWORK_PROMPT=0 \
  bash "${ROOT}/nexus.sh" --no-browser --no-tray || {
  echo "WARN: NEXUS panel start failed — see ${STATE}/panel-http.log" >&2
}

"${QUEEN}/scripts/run-queen.sh" || {
  echo "WARN: Queen start failed — see ${QUEEN}/.final-eye.log" >&2
}

if [[ -f "${ROOT}/lib/queen-layer-boot.sh" ]]; then
  # shellcheck source=/dev/null
  source "${ROOT}/lib/queen-layer-boot.sh"
  nexus_queen_layer_refresh 2>/dev/null || true
  nexus_queen_layer_install_autostart 2>/dev/null || true
fi

ready=0
for _ in $(seq 1 40); do
  curl -sf "http://127.0.0.1:${PANEL_PORT}/api/field-stack" >/dev/null 2>&1 && ready=$((ready + 1))
  curl -sf "http://127.0.0.1:${EYE_PORT}/api/health" >/dev/null 2>&1 && ready=$((ready + 1))
  curl -sf "http://127.0.0.1:${WORLD_PORT}/api/status" >/dev/null 2>&1 && ready=$((ready + 1))
  [[ "${ready}" -ge 3 ]] && break
  ready=0
  sleep 0.25
done

echo ""
echo "Field stack posture:"
pythong "${ROOT}/lib/queen_field_nexus.py" json 2>/dev/null | pythong -c "
import json, sys
doc = json.load(sys.stdin)
print('  Queen verdict:', doc.get('queen_verdict'))
print('  Gates held:   ', doc.get('gates_held'))
fe = doc.get('final_eye_weapons') or {}
print('  Final_Eye:    ', fe.get('teach_version'), fe.get('codename'))
print('  Mesh OK:      ', doc.get('eyeball', {}).get('mesh_ok'))
" 2>/dev/null || true

echo ""
echo "URLs:"
echo "  NEXUS panel  http://127.0.0.1:${PANEL_PORT}/field"
echo "  Final_Eye    http://127.0.0.1:${EYE_PORT}/ops"
echo "  AmmoCode     http://127.0.0.1:${AMMOCODE_PORT:-9555}/"
echo "  NEXUS C2       http://127.0.0.1:${PANEL_PORT}/field"
echo "  Grok AI Lab    http://127.0.0.1:${PANEL_PORT}/grok-lab"

if [[ "${NEXUS_FIELD_LAUNCH_BROWSER:-0}" == "1" ]] || [[ "${KILROY_LOAD_OS:-0}" == "1" ]]; then
  echo ""
  echo "=== Launch AmmoOS desktop (AMOURANTHRTX) ==="
  PY_LOAD="$(command -v pythong || command -v python3)"
  if [[ -f "${ROOT}/lib/field-queen-browser-open.py" ]] \
    && "$PY_LOAD" "${ROOT}/lib/field-queen-browser-open.py" desktop 2>/dev/null | grep -q '"ok": true'; then
    echo "  AmmoOS desktop — http://127.0.0.1:${PANEL_PORT}/field"
    echo "  Queen Browser (standalone) — http://127.0.0.1:${WORLD_PORT}/world/browser.html"
  else
    # shellcheck source=/dev/null
    [[ -f "${ROOT}/lib/panel-browser.sh" ]] && source "${ROOT}/lib/panel-browser.sh"
    if declare -f nexus_boot_c2_desktop >/dev/null 2>&1 && nexus_boot_c2_desktop; then
      echo "  AmmoOS desktop — icons + taskbar at http://127.0.0.1:${PANEL_PORT}/field"
      echo "  Queen Browser — http://127.0.0.1:${WORLD_PORT}/world/browser.html"
    else
      echo "  WARN: desktop launch incomplete — ./scripts/kilroy-load-os.sh" >&2
    fi
  fi
fi
