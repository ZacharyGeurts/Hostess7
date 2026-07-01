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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:nexus.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS Field OS — ./nexus.sh does it all: boot, panel, underlay, ZNetwork, Queen, Grok16.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
# Canonical field tree — NewLatest only (Queen, blocks, 2.0.0 gates).
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_FIELD_STANDALONE=1
export NEXUS_NEVER_HARM_OS="${NEXUS_NEVER_HARM_OS:-1}"
export ZNETWORK_NEVER_HARM_OS="${ZNETWORK_NEVER_HARM_OS:-1}"
export ZNETWORK_SMART_INSIDE="${ZNETWORK_SMART_INSIDE:-1}"
export ZNETWORK_RELAYER="${ZNETWORK_RELAYER:-1}"
export ZNETWORK_UNDERHOOK=0
export ZNETWORK_INTERNET_PIPE_TARGET="${ZNETWORK_INTERNET_PIPE_TARGET:-100}"
export ZNETWORK_MODE="${ZNETWORK_MODE:-ACTIVE}"
export QUEEN_BROWSER_ONLY="${QUEEN_BROWSER_ONLY:-0}"
export QUEEN_NO_OS_BROWSER="${QUEEN_NO_OS_BROWSER:-1}"
export NEXUS_BOOT_C2_ONLY="${NEXUS_BOOT_C2_ONLY:-1}"
export NEXUS_C2_DESKTOP_LAUNCH="${NEXUS_C2_DESKTOP_LAUNCH:-1}"
export QUEEN_BROWSER_HOME="${QUEEN_BROWSER_HOME:-http://127.0.0.1:${NEXUS_THREAT_PANEL_PORT:-9477}/field}"
export QUEEN_BROWSER_START="${QUEEN_BROWSER_START:-$QUEEN_BROWSER_HOME}"
export NEXUS_FIELD_BROWSER_QUEEN="${NEXUS_FIELD_BROWSER_QUEEN:-1}"
export NEXUS_FIELD_DNS="${NEXUS_FIELD_DNS:-1}"
export NEXUS_FIELD_DHCP="${NEXUS_FIELD_DHCP:-1}"
export NEXUS_FIELD_LOCAL_DNS_CONNECT="${NEXUS_FIELD_LOCAL_DNS_CONNECT:-1}"
export NEXUS_WAR_MACHINE="${NEXUS_WAR_MACHINE:-1}"
export NEXUS_C2_WAR_POSTURE="${NEXUS_C2_WAR_POSTURE:-1}"
export NEXUS_C2_KIOSK="${NEXUS_C2_KIOSK:-0}"
export NEXUS_EVERY_KILL_REKILL="${NEXUS_EVERY_KILL_REKILL:-1}"
export NEXUS_BOOT_REKILL="${NEXUS_BOOT_REKILL:-1}"
export NEXUS_FIELD_ATTACK_KIT="${NEXUS_FIELD_ATTACK_KIT:-1}"
export NEXUS_FIELD_AUTO_REKILL="${NEXUS_FIELD_AUTO_REKILL:-1}"
export NEXUS_ATTACK_KIT_AUTO_CRUSH="${NEXUS_ATTACK_KIT_AUTO_CRUSH:-1}"
export NEXUS_KILL_DETECT="${NEXUS_KILL_DETECT:-1}"
export SG_ROOT_KILL_PREJUDICE="${SG_ROOT_KILL_PREJUDICE:-1}"
export SG_ROOT_SOVEREIGN_KILL="${SG_ROOT_SOVEREIGN_KILL:-1}"
export SG_ROOT_SOVEREIGN_GUARD="${SG_ROOT_SOVEREIGN_GUARD:-1}"
export KILROY_WAR_POSTURE="${KILROY_WAR_POSTURE:-1}"
export FIELD_STACK_LAYER="${FIELD_STACK_LAYER:-hardware,nexus_c2,kilroy,ammoos,queen}"

# shellcheck source=/dev/null
source "${ROOT}/lib/nexus-common.sh"
nexus_init_runtime_paths
nexus_load_config 2>/dev/null || true
# shellcheck source=/dev/null
[[ -f "${ROOT}/lib/field-dns.sh" ]] && source "${ROOT}/lib/field-dns.sh"
declare -f nexus_field_services_boot >/dev/null 2>&1 && nexus_field_services_boot || true
# shellcheck source=/dev/null
[[ -f "${ROOT}/lib/nexus-boot-impl.sh" ]] && source "${ROOT}/lib/nexus-boot-impl.sh"
declare -f nexus_boot_impl_run >/dev/null 2>&1 && nexus_boot_impl_run || true
# shellcheck source=/dev/null
source "${ROOT}/lib/nexus-field-os.sh"
nexus_field_os_export_paths
# shellcheck source=/dev/null
source "${ROOT}/lib/panel-browser.sh"
# shellcheck source=/dev/null
source "${ROOT}/lib/panel-tray.sh"

nexus_resolve_panel_root() {
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/threat-panel-http.py" ]] \
    && [[ -d "${NEXUS_INSTALL_ROOT}/panel" ]]; then
    printf '%s' "${NEXUS_INSTALL_ROOT}"
    return 0
  fi
  local candidate
  for candidate in \
    "${NEXUS_PANEL_ROOT:-}" \
    "${ROOT}" \
    "${SG_ROOT:-}" \
    "${ROOT}/../NewLatest"; do
    [[ -n "$candidate" ]] || continue
    if [[ -f "${candidate}/lib/threat-panel-http.py" ]] && [[ -d "${candidate}/panel" ]]; then
      printf '%s' "${candidate}"
      return 0
    fi
  done
  printf '%s' "${NEXUS_INSTALL_ROOT}"
}

nexus_field_standalone_ensure_panel() {
  [[ "${NEXUS_FIELD_STANDALONE:-}" == "1" ]] || return 0

  local panel_root panel_py port cert key url ready_url want served
  panel_root="$(nexus_resolve_panel_root)"
  panel_py="${panel_root}/lib/threat-panel-http.py"
  [[ -f "$panel_py" ]] || {
    echo "BLOCKER: threat-panel-http.py not found — run from SG/NewLatest field tree." >&2
    return 1
  }
  [[ -d "${panel_root}/panel" ]] || {
    echo "BLOCKER: panel/ directory missing." >&2
    return 1
  }
  local pythong_bin="${NEXUS_PYTHONG:-$(nexus_resolve_pythong 2>/dev/null || true)}"
  [[ -n "$pythong_bin" && -x "$pythong_bin" ]] || {
    echo "BLOCKER: pythong required for panel." >&2
    echo "Expected: ${PYTHONG_ROOT:-${SG_ROOT}/PythonG}/bin/pythong or ${GPY16_ROOT:-${SG_ROOT}/GrokPy}/bin/gpy-16" >&2
    return 1
  }
  command -v curl >/dev/null 2>&1 || {
    echo "BLOCKER: curl required for panel health check." >&2
    return 1
  }

  nexus_ensure_dirs 2>/dev/null || mkdir -p "$NEXUS_STATE_DIR" 2>/dev/null || true
  # shellcheck source=/dev/null
  [[ -f "${panel_root}/lib/znetwork-field.sh" ]] && source "${panel_root}/lib/znetwork-field.sh"
  nexus_znetwork_publish 2>/dev/null || true

  want="$(nexus_panel_desired_version 2>/dev/null || true)"
  export NEXUS_THREAT_PANEL_PORT
  NEXUS_THREAT_PANEL_PORT="$(nexus_panel_pick_port "$want")"
  export NEXUS_THREAT_PANEL_PORT

  port="${NEXUS_THREAT_PANEL_PORT}"
  url="$(nexus_panel_url)"
  ready_url="$(nexus_panel_app_url)"

  if nexus_panel_needs_restart "$want"; then
    nexus_log "INFO" "nexus.sh" "PANEL_RESTART want=${want:-unknown} root=${panel_root}"
    nexus_panel_stop
  fi

  if ! pgrep -f "threat-panel-http.py.*${port}" >/dev/null 2>&1; then
    nohup env \
      NEXUS_INSTALL_ROOT="${panel_root}" \
      NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      TDIR="${TDIR:-${HOME}/.grok/projects/home-default-Desktop-SG/terminals}" \
      PATH="${PATH}" \
      SG_ROOT="${SG_ROOT}" \
      PYTHONG_ROOT="${PYTHONG_ROOT}" \
      GPY16_ROOT="${GPY16_ROOT}" \
      "$pythong_bin" "$panel_py" "$port" "${panel_root}/panel" \
      "${NEXUS_STATE_DIR}/threat-panel.json" \
      >>"${NEXUS_STATE_DIR}/panel-http.log" 2>&1 &
  fi

  if nexus_panel_wait_ready "$ready_url" 5 \
    || nexus_panel_wait_ready "$url" 5 \
    || nexus_panel_wait_ready "${url%/field}/" 5; then
    served="$(nexus_panel_served_version 2>/dev/null || true)"
    nexus_log "INFO" "nexus.sh" "PANEL_READY url=${url} version=${served:-unknown}"
    return 0
  fi

  echo "Panel not ready after start — see ${NEXUS_STATE_DIR}/panel-http.log" >&2
  return 1
}

nexus_panel_shutdown_immediate() {
  local port="${NEXUS_THREAT_PANEL_PORT:-9477}"
  if [[ -f "${ROOT}/lib/field-keyboard-sovereign.sh" ]]; then
    # shellcheck source=/dev/null
    source "${ROOT}/lib/field-keyboard-sovereign.sh"
    nexus_keyboard_sovereign_release "panel_shutdown"
  fi
  nexus_panel_tray_watchdog_stop 2>/dev/null || true
  nexus_panel_tray_stop 2>/dev/null || true
  pkill -9 -f 'threat-panel-http\.py' 2>/dev/null || true
  if command -v fuser >/dev/null 2>&1; then
    fuser -k "${port}/tcp" 2>/dev/null || true
    fuser -k "${NEXUS_THREAT_PANEL_FALLBACK_PORT:-9478}/tcp" 2>/dev/null || true
  fi
  nexus_await_port_free "${port}" 3 2>/dev/null || true
  rm -f "${NEXUS_STATE_DIR}/panel.pid" 2>/dev/null || true
  nexus_log "INFO" "nexus.sh" "PANEL_SHUTDOWN state=${NEXUS_STATE_DIR}"
}

nexus_panel_restart_immediate() {
  nexus_panel_shutdown_immediate
  nexus_field_standalone_ensure_panel
}

nexus_launch_underlay() {
  local mode="${1:-browser}"
  local url
  url="$(nexus_panel_tristate_url)"
  case "$mode" in
    zenity)
      exec pythong "${NEXUS_INSTALL_ROOT}/lib/field-underlay-switch.py" zenity
      ;;
    hotkey)
      exec pythong "${NEXUS_INSTALL_ROOT}/lib/field-underlay-hotkey.py" once
      ;;
  esac
  nexus_field_standalone_ensure_panel || true
  if nexus_panel_open_browser "$url"; then
    echo "Tristate Installer (Underlay F9): $url"
    nexus_panel_tray_install_autostart 2>/dev/null || true
    nexus_panel_tray_ensure_once 2>/dev/null || true
    return 0
  fi
  if command -v zenity >/dev/null 2>&1 && [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
    exec pythong "${NEXUS_INSTALL_ROOT}/lib/field-underlay-switch.py" zenity
  fi
  echo "Start NEXUS Field: ${NEXUS_INSTALL_ROOT}/nexus.sh" >&2
  echo "Then open: $url" >&2
  return 1
}

nexus_usage() {
  cat <<EOF
NEXUS Field OS — single launcher for panel, underlay, ZNetwork, Queen, Grok16, AmmoLang
  Version: $(nexus_read_version 2>/dev/null || echo unknown)
  Install: ${NEXUS_INSTALL_ROOT}
  State:   ${NEXUS_STATE_DIR}
  Grok16:  ${GROK16_ROOT:-${NEXUS_INSTALL_ROOT}/Grok16}

Usage:
  ./nexus.sh                 Boot stack → panel → underlay witness → NEXUS C2 desktop + tray
  ./nexus.sh --help          Show this help (-h, help)
  ./nexus.sh --url           Print panel URL only
  ./nexus.sh --wait          Block until panel responds
  ./nexus.sh --no-browser    Start panel; print URL and CLI hints (no browser)
  ./nexus.sh --no-tray       Skip system-tray icon (combine with other flags)
  ./nexus.sh --tray          Start tray icon only (right-click → jump to tab)
  ./nexus.sh --underlay      Open 2026 Tristate / Underlay F9 installer
  ./nexus.sh --drop-in       Forceful drop-in pipeline (defield → redata → secure net)
  ./nexus.sh --clean         Remove stale build trees (Queen/build, Grok16/build, …)
  ./nexus.sh --build         AmmoLang sovereign build (CHIPs → harness → forge)
  ./nexus.sh --browser-f9    F9 action once (Queen browser or Tristate installer)
  ./nexus.sh --tab <view>    Open a panel tab in the browser (e.g. command, library)
  ./nexus.sh --shutdown      Stop panel, tray, and watchdog immediately (--stop)
  ./nexus.sh --restart       Stop and start panel immediately (--restart-immediate)

Tab views (for --tab):
  command, us, field-broadcaster, field-obs, packets, threats, intel, final-eye, final-ear, final-mouth, signals, dns, outside, library, training, system
  Sub-views: packets/monitor, threats/map, intel/honor, system/settings, …

Environment:
  NEXUS_STATE_DIR      Field state directory (default: /var/lib/nexus-shield)
  NEXUS_PANEL_ROOT     Override panel install tree
  NEXUS_THREAT_PANEL_PORT  Panel HTTP port (default 9477)
  NEXUS_ZNETWORK_PROMPT    ZNetwork auto-activate on start (0=ingrained default, 1=legacy dialog)
  NEXUS_DIAGNOSTIC_MODE    Force diagnostic on (1) or off (0); unset = auto-engage on fault

CLI without browser:
  ./bin/nexus status
  ./bin/nexus panel --no-browser

Logs: \${NEXUS_STATE_DIR}/panel-http.log
EOF
}

case "${1:-}" in
  -h|--help|help)
    nexus_usage
    exit 0
    ;;
  --clean|--cleanup)
    nexus_field_os_build_clean
    exit $?
    ;;
  --build|--forge|--sovereign-build)
    nexus_field_os_sovereign_build
    exit $?
    ;;
  --underlay|--tristate|--install-gui)
    nexus_launch_underlay browser
    exit $?
    ;;
  --zenity)
    nexus_launch_underlay zenity
    exit $?
    ;;
  --hotkey|--browser-f9)
    nexus_launch_underlay hotkey
    exit $?
    ;;
  --drop-in)
    nexus_field_standalone_ensure_panel 2>/dev/null || true
    exec pythong "${NEXUS_INSTALL_ROOT}/lib/field-drop-in-orchestrator.py" pipeline
    ;;
  --shutdown|--stop)
    nexus_panel_shutdown_immediate
    echo "Panel stopped."
    exit 0
    ;;
  --restart|--restart-immediate)
    nexus_load_config 2>/dev/null || true
    # shellcheck source=/dev/null
    [[ -f "${ROOT}/lib/znetwork-field.sh" ]] && source "${ROOT}/lib/znetwork-field.sh"
    nexus_znetwork_startup_with_us || true
    if nexus_panel_restart_immediate; then
      URL="$(nexus_panel_url)"
      echo "Panel restarted: ${URL}"
      echo "Version: $(nexus_panel_served_version 2>/dev/null || nexus_panel_desired_version 2>/dev/null || echo unknown)"
      if [[ "${NEXUS_FIELD_LAUNCH_BROWSER:-1}" == "1" ]] && declare -f nexus_boot_c2_desktop >/dev/null 2>&1; then
        nexus_boot_c2_desktop && echo "NEXUS C2 desktop relaunched" \
          || echo "WARN: NEXUS C2 desktop launch incomplete — ./nexus.sh" >&2
      fi
      exit 0
    fi
    echo "Panel restart failed — see ${NEXUS_STATE_DIR}/panel-http.log" >&2
    exit 1
    ;;
esac

# Installed systems: try systemd only when not field-standalone.
if [[ "${NEXUS_FIELD_STANDALONE:-}" != "1" ]] \
  && [[ -f "${ROOT}/lib/nexus-daemon.sh" ]] && command -v systemctl >/dev/null 2>&1; then
  if ! systemctl is-active --quiet nexus-genius.service 2>/dev/null; then
    if [[ "$(id -u)" -eq 0 ]]; then
      systemctl start nexus-genius.service 2>/dev/null || true
    fi
  fi
fi

nexus_load_config 2>/dev/null || true
# ZNetwork relayer FIRST — sole internet in/out before front-hook / panel.
# shellcheck source=/dev/null
[[ -f "${ROOT}/lib/znetwork-field.sh" ]] && source "${ROOT}/lib/znetwork-field.sh"
nexus_znetwork_startup_with_us || true
[[ -f "${ROOT}/lib/front-hook.sh" ]] && {
  # shellcheck source=/dev/null
  source "${ROOT}/lib/front-hook.sh"
  nexus_front_hook_board 2>/dev/null || true
}
# Vestigial cleanup — old start menus, duplicate locations, legacy panels.
if [[ -f "${ROOT}/lib/nexus-vestigial-cleanup.sh" ]]; then
  # shellcheck source=/dev/null
  source "${ROOT}/lib/nexus-vestigial-cleanup.sh"
  nexus_vestigial_cleanup_run 2>/dev/null || true
fi
# Host OS — one AmmoOS start-menu entry + taskbar pin (idempotent).
nexus_field_os_install_host_desktop 2>/dev/null || true

nexus_field_standalone_ensure_panel || {
  echo "Try: ./nexus.sh --no-browser" >&2
  exit 1
}

nexus_field_os_underlay_witness 2>/dev/null || true

nexus_panel_publish_if_needed() {
  local panel_root="$1"
  local panel_json="${NEXUS_STATE_DIR}/threat-panel.json"
  [[ -f "${panel_root}/lib/threat-panel.sh" ]] || return 0
  # shellcheck source=/dev/null
  source "${panel_root}/lib/threat-panel.sh"
  if [[ -s "$panel_json" ]] && [[ "$(wc -c <"$panel_json" 2>/dev/null || echo 0)" -gt 32 ]]; then
    return 0
  fi
  local assemble="${panel_root}/scripts/panel-json-assemble.py"
  local pythong_bin="${NEXUS_PYTHONG:-$(nexus_resolve_pythong 2>/dev/null || true)}"
  if [[ -f "$assemble" && -n "$pythong_bin" && -x "$pythong_bin" ]]; then
    NEXUS_INSTALL_ROOT="${panel_root}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      "$pythong_bin" "$assemble" >/dev/null 2>&1 && return 0
  fi
  NEXUS_PANEL_PUBLISH_FAST="${NEXUS_PANEL_PUBLISH_FAST:-1}" \
    NEXUS_THREAT_PANEL=1 nexus_threat_panel_publish 2>/dev/null || true
}

panel_root="$(nexus_resolve_panel_root)"
nexus_panel_publish_if_needed "$panel_root"

URL="$(nexus_panel_url)"

if [[ "${1:-}" == "--url" ]]; then
  echo "$URL"
  exit 0
fi

if [[ "${1:-}" == "--wait" ]]; then
  if nexus_panel_wait_ready "$URL" 5; then
    echo "Panel ready: $URL ($(nexus_panel_served_version 2>/dev/null || echo unknown))"
    exit 0
  fi
  echo "Panel not ready: $URL" >&2
  exit 1
fi

if [[ "${1:-}" == "--no-tray" ]]; then
  export NEXUS_PANEL_TRAY=0
  shift
fi

if [[ "${1:-}" == "--no-browser" ]]; then
  echo "Panel: $URL"
  echo "Version: $(nexus_panel_served_version 2>/dev/null || nexus_panel_desired_version 2>/dev/null || echo unknown)"
  echo "State: ${NEXUS_STATE_DIR}"
  echo "Tools: ${NEXUS_FIELD_TOOLS_DIR:-${NEXUS_INSTALL_ROOT}/lib/bin}"
  nexus_panel_tray_install_autostart 2>/dev/null || true
  nexus_panel_tray_ensure_once 2>/dev/null || true
  nexus_boot_c2_prune_autostart 2>/dev/null || true
  nexus_panel_open_help "$URL"
  exit 0
fi

if [[ "${1:-}" == "--tray" ]]; then
  nexus_panel_tray_icon_refresh 2>/dev/null || true
  nexus_panel_tray_install_autostart 2>/dev/null || true
  nexus_boot_c2_prune_autostart 2>/dev/null || true
  nexus_panel_tray_ensure_once
  exit $?
fi

if [[ "${1:-}" == "--tab" && -n "${2:-}" ]]; then
  if [[ "${2}" == "underlay" || "${2}" == "tristate" ]]; then
    nexus_launch_underlay browser
    exit $?
  fi
  nexus_panel_open_tab "$2"
  nexus_panel_tray_ensure_once 2>/dev/null || true
  exit 0
fi

if nexus_boot_c2_desktop; then
  echo "NEXUS C2 war machine — command deck at ${URL}"
  nexus_panel_tray_install_autostart 2>/dev/null || true
  nexus_panel_tray_ensure_once 2>/dev/null || true
  exit 0
fi

echo "Could not launch NEXUS C2 desktop." >&2
nexus_panel_open_help "$URL" >&2
exit 1