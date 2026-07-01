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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/znetwork-field.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# ZNetwork — bottom-up networking for any OS; handoff without dropping the live link.

if [[ -f "${NEXUS_INSTALL_ROOT:-}/lib/nexus-polkit.sh" ]]; then
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/nexus-polkit.sh"
elif [[ -f "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/nexus-polkit.sh" ]]; then
  # shellcheck source=/dev/null
  source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/nexus-polkit.sh"
fi

if [[ -f "${NEXUS_INSTALL_ROOT:-}/lib/sg-paths.sh" ]]; then
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/sg-paths.sh"
  sg_paths_export_defaults 2>/dev/null || true
fi

# Canonical: NewLatest/ZNetwork only.
if [[ -z "${ZNETWORK_ROOT:-}" ]]; then
  if [[ -d "${NEXUS_INSTALL_ROOT:-}/ZNetwork" ]]; then
    ZNETWORK_ROOT="${NEXUS_INSTALL_ROOT}/ZNetwork"
  elif [[ -d "${NEXUS_INSTALL_ROOT:-}/../NewLatest/ZNetwork" ]]; then
    ZNETWORK_ROOT="$(cd "${NEXUS_INSTALL_ROOT}/../NewLatest/ZNetwork" && pwd)"
  else
    ZNETWORK_ROOT="${NEXUS_INSTALL_ROOT:-}/ZNetwork"
  fi
fi
ZNETWORK_BIN="${ZNETWORK_BIN:-}"
ZNETWORK_MODE="${ZNETWORK_MODE:-REVIEW_ONLY}"
ZNETWORK_DEFER_TRAY="${ZNETWORK_DEFER_TRAY:-0}"
ZNETWORK_RELAYER_MARKER="${NEXUS_STATE_DIR}/znetwork-relayer.json"
ZNETWORK_RELAYER_PY="${NEXUS_INSTALL_ROOT}/lib/znetwork-relayer.py"
# Deprecated — relayer replaces underhook
ZNETWORK_UNDERHOOK_MARKER="${ZNETWORK_RELAYER_MARKER}"
ZNETWORK_OPERATOR_JSON="${NEXUS_STATE_DIR}/znetwork-operator.json"
ZNETWORK_SKIP_MARKER="${NEXUS_STATE_DIR}/znetwork-skip.marker"
ZNETWORK_RUNNING_MARKER="${NEXUS_STATE_DIR}/znetwork-running.marker"
ZNETWORK_SOCK="${NEXUS_STATE_DIR}/znetwork-field.sock"
ZNETWORK_ORCHESTRATOR="${NEXUS_INSTALL_ROOT}/lib/znetwork-orchestrator.py"
ZNETWORK_HOSTILE_PY="${NEXUS_INSTALL_ROOT}/lib/znetwork-hostile-threat.py"
ZNETWORK_EXPLOIT_PY="${NEXUS_INSTALL_ROOT}/lib/znetwork-exploit-shield.py"
ZNETWORK_REPLACE_PY="${NEXUS_INSTALL_ROOT}/lib/znetwork-replace-in-place.py"
ZNETWORK_STARTUP_RETIRE_PY="${NEXUS_INSTALL_ROOT}/lib/znetwork-startup-retire.py"
ZNETWORK_WIRELESS_FCC_PY="${NEXUS_INSTALL_ROOT}/lib/znetwork-wireless-fcc.py"

nexus_znetwork_relayer() {
  [[ "${ZNETWORK_UNDERHOOK:-0}" != "1" ]] && [[ "${ZNETWORK_RELAYER:-1}" == "1" ]]
}

nexus_znetwork_smart_inside() {
  [[ "${ZNETWORK_SMART_INSIDE:-1}" == "1" ]]
}

nexus_znetwork_protection_only() {
  [[ "${ZNETWORK_PROTECTION_ONLY:-0}" == "1" ]]
}

# Restore host connectivity before relayer boards (NetworkManager may be masked after prior retire).
nexus_znetwork_ensure_host_network() {
  local iface ip_addr nm_state nm_enabled wifi_dev conn i=0
  if ip -4 route show default 2>/dev/null | grep -q .; then
    iface="$(ip -4 route show default 2>/dev/null | awk '{print $5; exit}')"
    if [[ -n "$iface" ]]; then
      ip_addr="$(ip -4 -o addr show dev "$iface" 2>/dev/null | awk '{print $4}' | head -1)"
      if [[ -n "$ip_addr" ]]; then
        nexus_znetwork_activate_log "host_network" "OK" "route_ok iface=${iface}"
        return 0
      fi
    fi
  fi

  nexus_znetwork_activate_log "host_network" "BEGIN" "restoring_connectivity"
  if [[ "$(id -u)" -ne 0 ]] && declare -f nexus_pol_has_cached_sudo >/dev/null 2>&1 \
    && ! nexus_pol_has_cached_sudo; then
    nexus_znetwork_prime_sudo_once || true
  fi

  if command -v systemctl >/dev/null 2>&1; then
    nm_state="$(systemctl is-active NetworkManager 2>/dev/null || echo inactive)"
    nm_enabled="$(systemctl is-enabled NetworkManager 2>/dev/null || echo unknown)"
    if [[ "$nm_state" != "active" ]]; then
      if [[ "$nm_enabled" == "masked" ]]; then
        sudo systemctl unmask NetworkManager 2>/dev/null \
          || pkexec systemctl unmask NetworkManager 2>/dev/null || true
      fi
      sudo systemctl enable NetworkManager 2>/dev/null \
        || systemctl enable NetworkManager 2>/dev/null || true
      sudo systemctl start NetworkManager 2>/dev/null \
        || systemctl start NetworkManager 2>/dev/null || true
      sleep 2
    fi
  fi

  if command -v nmcli >/dev/null 2>&1; then
    nmcli networking on 2>/dev/null || sudo nmcli networking on 2>/dev/null || true
    nmcli radio wifi on 2>/dev/null || sudo nmcli radio wifi on 2>/dev/null || true
    wifi_dev="$(nmcli -t -f DEVICE,TYPE,STATE dev status 2>/dev/null \
      | awk -F: '$2=="wifi" && $3!="unavailable" {print $1; exit}')"
    if [[ -n "$wifi_dev" ]]; then
      nmcli dev wifi rescan ifname "$wifi_dev" 2>/dev/null || true
      conn="$(nmcli -t -f GENERAL.CONNECTION dev show "$wifi_dev" 2>/dev/null \
        | head -1 | cut -d: -f2- | sed 's/^://')"
      if [[ -n "$conn" && "$conn" != "--" ]]; then
        nmcli connection up "$conn" ifname "$wifi_dev" 2>/dev/null \
          || sudo nmcli connection up "$conn" ifname "$wifi_dev" 2>/dev/null || true
      else
        nmcli dev connect "$wifi_dev" 2>/dev/null \
          || sudo nmcli dev connect "$wifi_dev" 2>/dev/null || true
      fi
    fi
  fi

  while [[ $i -lt 20 ]]; do
    if ip -4 route show default 2>/dev/null | grep -q .; then
      iface="$(ip -4 route show default 2>/dev/null | awk '{print $5; exit}')"
      ip_addr="$(ip -4 -o addr show dev "$iface" 2>/dev/null | awk '{print $4}' | head -1)"
      [[ -n "$ip_addr" ]] && {
        nexus_znetwork_activate_log "host_network" "OK" "route_restored iface=${iface}"
        return 0
      }
    fi
    sleep 1
    i=$((i + 1))
  done
  nexus_znetwork_activate_log "host_network" "WARN" "no_route_after_ensure"
  return 1
}

nexus_znetwork_install_autostart() {
  [[ "${ZNETWORK_AUTOSTART:-1}" == "1" ]] || return 0
  local home="${HOME:-/home/default}"
  local autostart="${home}/.config/autostart"
  local sg_root="${SG_ROOT:-}"
  local boot_script desktop release_install
  if [[ -z "$sg_root" || "$sg_root" == "${NEXUS_INSTALL_ROOT}" ]]; then
    sg_root="$(cd "${NEXUS_INSTALL_ROOT}/.." 2>/dev/null && pwd)"
  fi
  boot_script="${ZNETWORK_ROOT:-${NEXUS_INSTALL_ROOT}/ZNetwork}/scripts/znetwork-boot.sh"
  release_install="${ZNETWORK_ROOT:-${NEXUS_INSTALL_ROOT}/ZNetwork}/scripts/znetwork-release-install.sh"
  desktop="${autostart}/znetwork-boot.desktop"
  if [[ -x "$release_install" ]]; then
    SG_ROOT="${sg_root}" NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
      NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" HOME="${home}" \
      bash "$release_install" >/dev/null 2>&1 && {
      nexus_znetwork_activate_log "autostart" "OK" "installed=${desktop} via=release_install"
      return 0
    }
  fi
  [[ -f "$boot_script" ]] || boot_script="${NEXUS_INSTALL_ROOT}/scripts/znetwork-login-boot.sh"
  [[ -f "$boot_script" ]] || {
    nexus_znetwork_activate_log "autostart" "SKIP" "boot_script_missing"
    return 0
  }
  mkdir -p "$autostart" 2>/dev/null || return 0
  cat >"$desktop" <<EOF
[Desktop Entry]
Type=Application
Name=ZNetwork Boot
Comment=Restore NetworkManager and board ZNetwork relayer after login
Icon=network-workgroup
Exec=env SG_ROOT=${sg_root} NEXUS_INSTALL_ROOT=${NEXUS_INSTALL_ROOT} NEXUS_STATE_DIR=${NEXUS_STATE_DIR} ZNETWORK_ROOT=${ZNETWORK_ROOT:-${NEXUS_INSTALL_ROOT}/ZNetwork} DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus bash ${boot_script}
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
StartupNotify=false
EOF
  chmod 644 "$desktop" 2>/dev/null || true
  nexus_znetwork_activate_log "autostart" "OK" "installed=${desktop}"
}

nexus_znetwork_takeover_active() {
  nexus_znetwork_smart_inside && return 1
  nexus_znetwork_protection_only && return 1
  [[ "${ZNETWORK_MODE:-REVIEW_ONLY}" == "ACTIVE" || "${ZNETWORK_TAKEOVER:-0}" == "1" ]]
}

# Prime sudo once — avoids double password prompts during underhook + takeover.
nexus_znetwork_prime_sudo_once() {
  [[ "$(id -u)" -eq 0 ]] && { export NEXUS_ELEVATED_ROOT=1; return 0; }
  if declare -f nexus_pol_has_cached_sudo >/dev/null 2>&1 && nexus_pol_has_cached_sudo; then
    declare -f nexus_pol_start_sudo_keepalive >/dev/null 2>&1 && nexus_pol_start_sudo_keepalive 2>/dev/null || true
    export NEXUS_ELEVATED_ROOT=1
    nexus_znetwork_activate_log "sudo_prime" "OK" "cached"
    return 0
  fi
  local pw="${SUDO_PASSWORD:-${NEXUS_SUDO_PASSWORD:-}}"
  if [[ -n "$pw" ]]; then
    printf '%s\n' "$pw" | sudo -S -v 2>/dev/null && {
      declare -f nexus_pol_start_sudo_keepalive >/dev/null 2>&1 && nexus_pol_start_sudo_keepalive 2>/dev/null || true
      export NEXUS_ELEVATED_ROOT=1
      nexus_znetwork_activate_log "sudo_prime" "OK" "password_env"
      unset pw
      return 0
    }
    unset pw
  fi
  if [[ "${ZNETWORK_FAST:-0}" == "1" ]] || [[ ! -t 0 ]]; then
    nexus_znetwork_activate_log "sudo_prime" "SKIP" "non_interactive_no_cache"
    return 1
  fi
  if declare -f nexus_pol_secure_sudo >/dev/null 2>&1 && nexus_pol_secure_sudo "ZNetwork — authenticate once for network handoff."; then
    declare -f nexus_pol_start_sudo_keepalive >/dev/null 2>&1 && nexus_pol_start_sudo_keepalive 2>/dev/null || true
    export NEXUS_ELEVATED_ROOT=1
    nexus_znetwork_activate_log "sudo_prime" "OK" "secure_sudo"
    return 0
  fi
  nexus_znetwork_activate_log "sudo_prime" "FAIL" "no_auth"
  return 1
}

nexus_znetwork_bin() {
  local candidate
  for candidate in \
    "${ZNETWORK_BIN}" \
    "${NEXUS_INSTALL_ROOT}/ZNetwork/build/znetwork" \
    "${ZNETWORK_ROOT}/build/znetwork" \
    "${NEXUS_INSTALL_ROOT}/bin/znetwork" \
    "${NEXUS_INSTALL_ROOT}/bin/znetwork.exe" \
    "${NEXUS_INSTALL_ROOT}/ZNetwork/build/znetwork.exe"; do
    [[ -n "$candidate" && -x "$candidate" ]] || continue
    printf '%s' "$candidate"
    return 0
  done
  return 1
}

nexus_znetwork_review_gate_script() {
  local candidate
  for candidate in \
    "${NEXUS_INSTALL_ROOT}/ZNetwork/scripts/znetwork-review-gate.sh" \
    "${ZNETWORK_ROOT}/scripts/znetwork-review-gate.sh" \
    "${NEXUS_INSTALL_ROOT}/znetwork/scripts/znetwork-review-gate.sh"; do
    [[ -x "$candidate" ]] || continue
    printf '%s' "$candidate"
    return 0
  done
  return 1
}

nexus_znetwork_hostile_py() {
  local runner="${NEXUS_PYTHONG:-pythong}"
  command -v "$runner" >/dev/null 2>&1 || runner="python3"
  [[ -f "${ZNETWORK_HOSTILE_PY}" ]] || return 1
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    "$runner" "${ZNETWORK_HOSTILE_PY}" "$@"
}

nexus_znetwork_hostile_scan() {
  if nexus_znetwork_hostile_py scan >/dev/null 2>&1; then
    nexus_znetwork_activate_log "hostile_scan" "OK" "immediate_iff"
    return 0
  fi
  if nexus_znetwork_orchestrator_py hostile-scan >/dev/null 2>&1; then
    nexus_znetwork_activate_log "hostile_scan" "OK" "via=orchestrator"
    return 0
  fi
  nexus_znetwork_activate_log "hostile_scan" "SKIP" "hostile_module_unavailable"
  return 0
}

nexus_znetwork_exploit_py() {
  local runner="${NEXUS_PYTHONG:-pythong}"
  command -v "$runner" >/dev/null 2>&1 || runner="python3"
  [[ -f "${ZNETWORK_EXPLOIT_PY}" ]] || return 1
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    "$runner" "${ZNETWORK_EXPLOIT_PY}" "$@"
}

nexus_znetwork_exploit_scan() {
  if nexus_znetwork_exploit_py scan >/dev/null 2>&1; then
    nexus_znetwork_activate_log "exploit_scan" "OK" "behavioral_zero_day"
    return 0
  fi
  if nexus_znetwork_orchestrator_py exploit-scan >/dev/null 2>&1; then
    nexus_znetwork_activate_log "exploit_scan" "OK" "via=orchestrator"
    return 0
  fi
  nexus_znetwork_activate_log "exploit_scan" "SKIP" "exploit_shield_unavailable"
  return 0
}

nexus_znetwork_exploit_watch() {
  if nexus_znetwork_exploit_py watch >/dev/null 2>&1; then
    nexus_znetwork_activate_log "exploit_watch" "OK" "confirmed_only_interdict"
    return 0
  fi
  if nexus_znetwork_orchestrator_py exploit-watch >/dev/null 2>&1; then
    nexus_znetwork_activate_log "exploit_watch" "OK" "via=orchestrator"
    return 0
  fi
  nexus_znetwork_activate_log "exploit_watch" "SKIP" "exploit_shield_unavailable"
  return 0
}

nexus_znetwork_hostile_respond() {
  if nexus_znetwork_hostile_py countermeasure >/dev/null 2>&1; then
    nexus_znetwork_activate_log "hostile_respond" "OK" "zero_hesitation"
    return 0
  fi
  if nexus_znetwork_orchestrator_py hostile-respond >/dev/null 2>&1; then
    nexus_znetwork_activate_log "hostile_respond" "OK" "via=orchestrator"
    return 0
  fi
  nexus_znetwork_activate_log "hostile_respond" "SKIP" "hostile_module_unavailable"
  return 0
}

nexus_znetwork_orchestrator_py() {
  local runner="${NEXUS_PYTHONG:-pythong}"
  command -v "$runner" >/dev/null 2>&1 || runner="python3"
  [[ -f "${ZNETWORK_ORCHESTRATOR}" ]] || return 1
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
  ZNETWORK_BIN="$(nexus_znetwork_bin 2>/dev/null || true)" \
  ZNETWORK_MODE="${ZNETWORK_MODE}" \
    "$runner" "${ZNETWORK_ORCHESTRATOR}" "$@"
}

nexus_znetwork_write_operator() {
  local choice="$1"
  local running="${2:-0}"
  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true
  printf '{"choice":"%s","running":%s,"mode":"%s","updated":"%s","orchestrator":"znetwork-orchestrator/v2"}\n' \
    "$choice" "$running" "${ZNETWORK_MODE}" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
    >"${ZNETWORK_OPERATOR_JSON}" 2>/dev/null || true
  if [[ "$choice" == "yes" && "$running" == "true" ]]; then
    : >"${ZNETWORK_RUNNING_MARKER}" 2>/dev/null || true
    chmod 600 "${ZNETWORK_RUNNING_MARKER}" 2>/dev/null || true
  else
    rm -f "${ZNETWORK_RUNNING_MARKER}" 2>/dev/null || true
  fi
}

nexus_znetwork_is_running() {
  [[ -f "${ZNETWORK_RUNNING_MARKER}" ]] && return 0
  [[ -S "${ZNETWORK_SOCK}" ]] && return 0
  if [[ -f "${ZNETWORK_OPERATOR_JSON}" ]]; then
    grep -q '"running"[[:space:]]*:[[:space:]]*true' "${ZNETWORK_OPERATOR_JSON}" 2>/dev/null \
      && grep -q '"choice"[[:space:]]*:[[:space:]]*"yes"' "${ZNETWORK_OPERATOR_JSON}" 2>/dev/null \
      && return 0
  fi
  pgrep -f '[z]network.*policy' >/dev/null 2>&1 && return 0
  return 1
}

nexus_znetwork_replace_py() {
  local runner="${NEXUS_PYTHONG:-pythong}"
  command -v "$runner" >/dev/null 2>&1 || runner="python3"
  [[ -f "${ZNETWORK_REPLACE_PY}" ]] || return 1
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
  ZNETWORK_SMART_INSIDE=1 \
  ZNETWORK_TAKEOVER=0 \
  ZNETWORK_NEVER_HARM_OS=1 \
  NEXUS_NEVER_HARM_OS=1 \
  NEXUS_ZNETWORK_NO_SUDO="${NEXUS_ZNETWORK_NO_SUDO:-0}" \
    "$runner" "${ZNETWORK_REPLACE_PY}" "$@"
}

nexus_znetwork_kill_and_replace() {
  # In-place replace: retire old destructive stack, install smart inside + exploit shield.
  nexus_znetwork_activate_log "kill_replace" "BEGIN" "in_place_replace=1"
  nexus_znetwork_write_operator "no" "false"
  if nexus_znetwork_replace_py replace >/dev/null 2>&1; then
    nexus_znetwork_activate_log "kill_replace" "OK" "smart_inside_replaced_old"
    nexus_znetwork_startup_retire_host || true
    return 0
  fi
  rm -f "${ZNETWORK_RUNNING_MARKER}" "${ZNETWORK_SOCK}" "${ZNETWORK_SKIP_MARKER}" 2>/dev/null || true
  local pid
  for pid in $(pgrep -f 'znetwork-orchestrator\.py|znetwork-review-gate\.sh|znetwork-hostile-threat\.py|znetwork-os-takeover\.py' 2>/dev/null || true); do
    kill -TERM "$pid" 2>/dev/null || true
  done
  nexus_znetwork_handler_retire_py retire >/dev/null 2>&1 || true
  sleep 0.15
  nexus_znetwork_activate_log "kill_replace" "OK" "fallback_cleared_stale_pids"
}

nexus_znetwork_mark_running() {
  if [[ "${ZNETWORK_FAST:-0}" != "1" ]] \
    && declare -f nexus_znetwork_orchestrator_py >/dev/null 2>&1 \
    && timeout 8 nexus_znetwork_orchestrator_py mark-running >/dev/null 2>&1; then
    return 0
  fi
  nexus_znetwork_write_operator "yes" "true"
  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true
  rm -f "${ZNETWORK_SKIP_MARKER}" 2>/dev/null || true
  : >"${ZNETWORK_RUNNING_MARKER}" 2>/dev/null || true
  chmod 600 "${ZNETWORK_RUNNING_MARKER}" 2>/dev/null || true
}

nexus_znetwork_activate_log() {
  local step="$1" status="$2" detail="${3:-}"
  local log="${NEXUS_STATE_DIR}/znetwork-activate.jsonl"
  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true
  printf '{"ts":"%s","step":"%s","status":"%s","detail":"%s"}\n' \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$step" "$status" "$detail" >>"$log" 2>/dev/null || true
  nexus_log "INFO" "znetwork" "ACTIVATE_${status} step=${step} ${detail}"
}

nexus_znetwork_tray_silent() {
  # Soft restart — visible znetwork taskbar icon (not deferred/invisible).
  [[ "${NEXUS_PANEL_TRAY:-1}" == "1" ]] || return 0
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/panel-tray.sh" ]] || return 0
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/panel-tray.sh"
  export NEXUS_TRAY_MODE=znetwork
  export NEXUS_TRAY_ICON_REFRESH=1
  export ZNETWORK_DEFER_TRAY=0
  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true
  printf '{"schema":"znetwork-tray-mode/v2","mode":"znetwork","app_id":"znetwork-field-panel","icon":"znetwork-tray","active":true,"visible":true,"title":"ZNetwork Relayer","swapped_at":"%s"}\n' \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >"${NEXUS_STATE_DIR}/znetwork-tray-mode.json" 2>/dev/null || true
  nexus_panel_tray_icon_refresh 2>/dev/null || true
  if nexus_panel_tray_is_running; then
    nexus_panel_tray_stop_app 2>/dev/null || true
    sleep 0.3
  fi
  nexus_panel_tray_start >/dev/null 2>&1 || true
  nexus_panel_tray_watchdog_start >/dev/null 2>&1 || true
  nexus_znetwork_activate_log "tray_silent" "OK" "mode=znetwork visible=1 restart=soft"
  return 0
}

nexus_znetwork_tray_swap() {
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/panel-tray.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/panel-tray.sh"
    export NEXUS_TRAY_MODE=znetwork
    export NEXUS_TRAY_ICON_REFRESH=1
    nexus_panel_tray_znetwork_swap 2>/dev/null && {
      nexus_znetwork_activate_log "tray_swap" "OK" "mode=znetwork"
      return 0
    }
  fi
  if nexus_znetwork_orchestrator_py tray-swap >/dev/null 2>&1; then
    nexus_znetwork_activate_log "tray_swap" "OK" "orchestrator"
    return 0
  fi
  nexus_znetwork_activate_log "tray_swap" "FAIL" "no_tray_or_display"
  return 1
}

nexus_znetwork_handler_retire_py() {
  local runner="${NEXUS_PYTHONG:-pythong}"
  command -v "$runner" >/dev/null 2>&1 || runner="python3"
  local py="${NEXUS_INSTALL_ROOT}/lib/znetwork-handler-retire.py"
  [[ -f "$py" ]] || return 1
  local fast_limit=5
  case "${1:-}" in
    replace|retire) fast_limit=25 ;;
  esac
  if [[ "${ZNETWORK_FAST:-0}" == "1" ]]; then
    timeout "$fast_limit" env NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
      NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      ZNETWORK_BIN="$(nexus_znetwork_bin 2>/dev/null || true)" \
      "$runner" "$py" "$@"
    return $?
  fi
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
  ZNETWORK_BIN="$(nexus_znetwork_bin 2>/dev/null || true)" \
    "$runner" "$py" "$@"
}

nexus_znetwork_never_harm_os() {
  [[ "${ZNETWORK_NEVER_HARM_OS:-${NEXUS_NEVER_HARM_OS:-1}}" != "0" ]]
}

nexus_znetwork_retire_legacy_handlers() {
  nexus_znetwork_handler_retire_py retire >/dev/null 2>&1 && {
    if nexus_znetwork_never_harm_os; then
      nexus_znetwork_activate_log "handler_retire" "OK" "coexist_os_bypass_only"
    else
      nexus_znetwork_activate_log "handler_retire" "OK" "graceful_no_sudo"
    fi
    return 0
  }
  nexus_znetwork_activate_log "handler_retire" "SKIP" "handler_retire_unavailable"
  return 0
}

nexus_znetwork_startup_retire_py() {
  local runner="${NEXUS_PYTHONG:-pythong}"
  command -v "$runner" >/dev/null 2>&1 || runner="python3"
  local py="${ZNETWORK_STARTUP_RETIRE_PY}"
  [[ -f "$py" ]] || return 1
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
  ZNETWORK_STARTUP_RETIRE="${ZNETWORK_STARTUP_RETIRE:-1}" \
    "$runner" "$py" "$@"
}

nexus_znetwork_wireless_fcc_py() {
  local runner="${NEXUS_PYTHONG:-pythong}"
  command -v "$runner" >/dev/null 2>&1 || runner="python3"
  local py="${ZNETWORK_WIRELESS_FCC_PY}"
  [[ -f "$py" ]] || return 1
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    "$runner" "$py" "$@"
}

nexus_znetwork_wireless_fcc_bind_and_scan() {
  nexus_znetwork_wireless_fcc_py bind >/dev/null 2>&1 || return 0
  nexus_znetwork_wireless_fcc_py scan >/dev/null 2>&1 && {
    nexus_znetwork_activate_log "wireless_fcc" "OK" "fcc_only_trace_strike"
    return 0
  }
  nexus_znetwork_activate_log "wireless_fcc" "SKIP" "scan_unavailable"
  return 0
}

nexus_znetwork_startup_retire_host() {
  [[ "${ZNETWORK_STARTUP_RETIRE:-1}" == "1" ]] || {
    nexus_znetwork_activate_log "startup_retire" "SKIP" "env_disabled"
    return 0
  }
  nexus_znetwork_is_running || {
    nexus_znetwork_activate_log "startup_retire" "SKIP" "znetwork_not_running"
    return 0
  }
  local rep needs_reboot=0 retired=0
  rep="$(nexus_znetwork_startup_retire_py retire 2>/dev/null || true)"
  if grep -q '"skipped"[[:space:]]*:[[:space:]]*true' <<<"$rep" 2>/dev/null; then
    nexus_znetwork_activate_log "startup_retire" "SKIP" "$(sed -n 's/.*"reason"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' <<<"$rep" | head -1)"
    return 0
  fi
  grep -q '"needs_reboot"[[:space:]]*:[[:space:]]*true' <<<"$rep" 2>/dev/null && needs_reboot=1
  retired="$(sed -n 's/.*"retired_count"[[:space:]]*:[[:space:]]*\([0-9]*\).*/\1/p' <<<"$rep" | head -1)"
  [[ -n "$retired" && "$retired" -gt 0 ]] 2>/dev/null && {
    nexus_znetwork_activate_log "startup_retire" "OK" "retired=${retired} needs_reboot=${needs_reboot}"
    [[ "$needs_reboot" -eq 1 ]] && : >"${NEXUS_STATE_DIR}/znetwork-needs-reboot.marker" 2>/dev/null || true
    return 0
  }
  nexus_znetwork_activate_log "startup_retire" "OK" "nothing_to_retire"
  return 0
}

nexus_znetwork_replace_connection() {
  nexus_znetwork_handler_retire_py replace >/dev/null 2>&1 && {
    nexus_znetwork_activate_log "replace_connection" "OK" "policy_owner=znetwork"
    return 0
  }
  nexus_znetwork_activate_log "replace_connection" "SKIP" "replace_unavailable"
  return 0
}

# Pol root gate — optional; skipped when NEXUS_ZNETWORK_NO_SUDO=1.
nexus_znetwork_pol_root_gate() {
  [[ "${NEXUS_ZNETWORK_NO_SUDO:-0}" == "1" ]] && {
    nexus_znetwork_activate_log "pol_root" "SKIP" "no_sudo_user_space"
    return 0
  }
  local pol_json root_ok=0
  if ! declare -f nexus_pol_ensure_root >/dev/null 2>&1; then
    nexus_znetwork_activate_log "pol_root" "SKIP" "nexus-polkit.sh missing"
    return 0
  fi
  pol_json="$(nexus_pol_root_json znetwork 2>/dev/null || true)"
  if [[ -n "$pol_json" ]]; then
    nexus_znetwork_activate_log "pol_root" "OK" "$pol_json"
    grep -q '"is_root"[[:space:]]*:[[:space:]]*true' <<<"$pol_json" 2>/dev/null && root_ok=1
    grep -q '"has_cached_sudo"[[:space:]]*:[[:space:]]*true' <<<"$pol_json" 2>/dev/null && root_ok=1
  fi
  if [[ "$root_ok" -eq 1 ]] || nexus_pol_is_root znetwork 2>/dev/null; then
    export NEXUS_ELEVATED_ROOT=1
    nexus_znetwork_activate_log "pol_elevated" "OK" "already_root_or_cached_sudo"
    return 0
  fi
  if nexus_pol_ensure_root znetwork; then
    export NEXUS_ELEVATED_ROOT=1
    nexus_znetwork_activate_log "pol_elevated" "OK" "secure_elevation"
    return 0
  fi
  nexus_znetwork_activate_log "pol_elevated" "FAIL" "operator_declined_or_no_gui"
  return 1
}

nexus_znetwork_user_attach() {
  local bin iface shadow="${NEXUS_STATE_DIR}/znetwork-shadow.json"
  bin="$(nexus_znetwork_bin)" || return 1
  iface="$("${bin}" probe --json 2>/dev/null | sed -n 's/.*"iface"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
  [[ -n "$iface" ]] || iface="$(ip -4 route show default 2>/dev/null | awk '{print $5; exit}')"

  if [[ -f "${NEXUS_STATE_DIR}/znetwork-status.json" ]]; then
    cp -f "${NEXUS_STATE_DIR}/znetwork-status.json" "$shadow" 2>/dev/null || true
    nexus_znetwork_activate_log "shadow_mirror" "OK" "file=${shadow}"
  fi

  nexus_znetwork_replace_connection || true
  nexus_znetwork_activate_log "protection_snapshot" "OK" "iface=${iface:-unknown} coexist_os=1"
  return 0
}

nexus_znetwork_ensure_tray() {
  [[ "${NEXUS_PANEL_TRAY:-1}" == "1" ]] || return 0
  nexus_znetwork_is_running || return 0
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/panel-tray.sh" ]] || return 0
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/panel-tray.sh"
  local mode
  mode="$(nexus_panel_tray_mode)"
  if [[ "$mode" != "znetwork" ]] || ! nexus_panel_tray_is_running; then
    export NEXUS_TRAY_MODE=znetwork
    export NEXUS_TRAY_ICON_REFRESH=1
    nexus_panel_tray_znetwork_swap 2>/dev/null || true
    nexus_znetwork_activate_log "ensure_tray" "OK" "mode=znetwork running=$(nexus_panel_tray_is_running && echo 1 || echo 0)"
  fi
  if nexus_znetwork_relayer; then
    nexus_znetwork_relayer_watch || true
  elif ! nexus_znetwork_protection_only; then
    nexus_znetwork_exploit_scan || true
    nexus_znetwork_hostile_scan || true
    nexus_znetwork_hostile_respond || true
  fi
}

nexus_znetwork_relayer_py() {
  local runner="${NEXUS_PYTHONG:-pythong}"
  command -v "$runner" >/dev/null 2>&1 || runner="python3"
  [[ -f "${ZNETWORK_RELAYER_PY}" ]] || return 1
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
  ZNETWORK_RELAYER=1 \
  ZNETWORK_UNDERHOOK=0 \
  ZNETWORK_SMART_INSIDE=1 \
  ZNETWORK_TAKEOVER=0 \
    "$runner" "${ZNETWORK_RELAYER_PY}" "$@"
}

nexus_znetwork_pol_elevate_relayer() {
  # Relayer — pol elevation before relay owns internet in/out.
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/nexus-polkit.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/nexus-polkit.sh"
  elif [[ -f "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/nexus-polkit.sh" ]]; then
    # shellcheck source=/dev/null
    source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/nexus-polkit.sh"
  else
    nexus_znetwork_activate_log "pol_elevate" "SKIP" "nexus-polkit.sh missing"
    return 0
  fi
  if nexus_pol_is_root znetwork 2>/dev/null; then
    export NEXUS_ELEVATED_ROOT=1
    nexus_znetwork_activate_log "pol_elevate" "OK" "already_root"
    return 0
  fi
  if nexus_pol_has_cached_sudo 2>/dev/null; then
    nexus_pol_start_sudo_keepalive 2>/dev/null || true
    export NEXUS_ELEVATED_ROOT=1
    nexus_znetwork_activate_log "pol_elevate" "OK" "cached_sudo"
    return 0
  fi
  if nexus_znetwork_prime_sudo_once; then
    return 0
  fi
  if [[ "${ZNETWORK_FAST:-0}" == "1" ]] || [[ ! -t 0 ]]; then
    nexus_znetwork_activate_log "pol_elevate" "SKIP" "fast_or_non_interactive"
    return 0
  fi
  if timeout 8 nexus_pol_ensure_root znetwork; then
    export NEXUS_ELEVATED_ROOT=1
    nexus_znetwork_activate_log "pol_elevate" "OK" "pol_ensure_root"
    return 0
  fi
  nexus_znetwork_activate_log "pol_elevate" "PARTIAL" "declined_or_no_gui"
  return 0
}

nexus_znetwork_triple_check_fast() {
  local bin out="${NEXUS_STATE_DIR}/znetwork-status.json"
  bin="$(nexus_znetwork_bin)" || return 1
  export SG_ROOT="${SG_ROOT:-$(cd "${NEXUS_INSTALL_ROOT}/.." 2>/dev/null && pwd)}"
  export ZNETWORK_MODE="${ZNETWORK_MODE}"
  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true
  timeout 8 "${bin}" probe --json >/dev/null 2>&1 \
    || ip -4 route show default >/dev/null 2>&1 || return 1
  if timeout 8 "${bin}" status --json >"${out}.tmp" 2>/dev/null; then
    mv -f "${out}.tmp" "${out}" 2>/dev/null || cp "${out}.tmp" "${out}" 2>/dev/null || true
    rm -f "${out}.tmp" 2>/dev/null || true
    return 0
  fi
  rm -f "${out}.tmp" 2>/dev/null || true
  return 1
}

nexus_znetwork_relayer_already_active() {
  [[ -f "${ZNETWORK_RELAYER_MARKER}" ]] || return 1
  grep -q '"active"[[:space:]]*:[[:space:]]*true' "${ZNETWORK_RELAYER_MARKER}" 2>/dev/null || return 1
  nexus_znetwork_is_running || return 1
  return 0
}

nexus_znetwork_relayer_board() {
  # Relayer — sole internet in/out stack; civilian passes, hostile nuked immediately.
  [[ "${NEXUS_ZNETWORK:-1}" == "1" ]] || return 0
  [[ "${ZNETWORK_RELAYER:-1}" == "1" ]] || return 0
  [[ "${ZNETWORK_UNDERHOOK:-0}" == "1" ]] && return 1
  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true
  export ZNETWORK_RELAYER=1
  export ZNETWORK_UNDERHOOK=0
  export ZNETWORK_FAST="${ZNETWORK_FAST:-1}"
  export ZNETWORK_TAKEOVER=0
  export NEXUS_ZNETWORK_NO_SUDO="${NEXUS_ZNETWORK_NO_SUDO:-0}"
  export ZNETWORK_NEVER_HARM_OS="${ZNETWORK_NEVER_HARM_OS:-1}"
  export NEXUS_NEVER_HARM_OS="${NEXUS_NEVER_HARM_OS:-1}"
  export SG_ROOT="${SG_ROOT:-$(cd "${NEXUS_INSTALL_ROOT}/.." 2>/dev/null && pwd)}"
  export ZNETWORK_SMART_INSIDE="${ZNETWORK_SMART_INSIDE:-1}"
  export ZNETWORK_PROTECTION_ONLY="${ZNETWORK_PROTECTION_ONLY:-0}"
  export ZNETWORK_NO_REVIEW="${ZNETWORK_NO_REVIEW:-1}"
  export ZNETWORK_REVIEW_APPROVED="${ZNETWORK_REVIEW_APPROVED:-1}"
  export ZNETWORK_LAB_GATE_OK="${ZNETWORK_LAB_GATE_OK:-1}"
  local bin eff
  bin="$(nexus_znetwork_bin 2>/dev/null || true)"
  if [[ -n "$bin" ]]; then
    eff="$("${bin}" mode ACTIVE --json 2>/dev/null || true)"
    if grep -q '"effective":"ACTIVE"' <<<"$eff" 2>/dev/null; then
      export ZNETWORK_MODE=ACTIVE
    fi
  fi
  nexus_znetwork_bin >/dev/null 2>&1 || {
    nexus_log "WARN" "znetwork" "RELAYER_SKIP reason=binary_missing"
    return 0
  }
  [[ -f "${NEXUS_STATE_DIR}/znetwork-skip.marker" ]] && return 0
  if [[ "${ZNETWORK_FORCE_REBOARD:-0}" != "1" ]] && nexus_znetwork_relayer_already_active; then
    nexus_znetwork_relayer_watch || true
    nexus_znetwork_ensure_tray 2>/dev/null || true
    nexus_log "INFO" "znetwork" "RELAYER_SKIP reason=already_active"
    return 0
  fi
  export ZNETWORK_INVISIBLE_REPLACE="${ZNETWORK_INVISIBLE_REPLACE:-1}"
  export ZNETWORK_LINK_PRESERVE="${ZNETWORK_LINK_PRESERVE:-1}"
  export ZNETWORK_DEFER_RETALIATE="${ZNETWORK_DEFER_RETALIATE:-1}"
  nexus_znetwork_ensure_host_network || true
  nexus_znetwork_pol_elevate_relayer || true
  nexus_znetwork_kill_and_replace
  nexus_log "INFO" "znetwork" "RELAYER_BOARD mode=${ZNETWORK_MODE} invisible=${ZNETWORK_INVISIBLE_REPLACE:-1}"
  if nexus_znetwork_relayer_py relay >/dev/null 2>&1; then
    nexus_znetwork_mark_running
    nexus_znetwork_startup_retire_host || true
    nexus_znetwork_wireless_fcc_bind_and_scan || true
    nexus_znetwork_activate_log "relayer_activate" "OK" "invisible=1 link_preserve=1"
    nexus_log "INFO" "znetwork" "RELAYER_OK invisible=1 no_drop=1"
    (
      sleep "${ZNETWORK_ARM_DELAY_SEC:-12}"
      nexus_znetwork_relayer_py arm >/dev/null 2>&1 || true
      if [[ "${ZNETWORK_DEFER_TRAY:-0}" == "1" ]]; then
        nexus_znetwork_tray_silent >/dev/null 2>&1 || true
      else
        nexus_znetwork_tray_swap >/dev/null 2>&1 || true
      fi
    ) &
    return 0
  fi
  nexus_znetwork_activate_log "relayer_activate" "FAIL" "relay_command_failed"
  return 1
}

nexus_znetwork_relayer_watch() {
  nexus_znetwork_relayer_py watch >/dev/null 2>&1 || true
}

# Deprecated aliases — underhook removed, relayer owns startup
nexus_znetwork_pol_elevate_underhook() { nexus_znetwork_pol_elevate_relayer "$@"; }
nexus_znetwork_underhook_already_boarded() { nexus_znetwork_relayer_already_active; }
nexus_znetwork_underhook_board() { nexus_znetwork_relayer_board; }
nexus_znetwork_underhook_activate() { nexus_znetwork_relayer_board; }

nexus_znetwork_activate_on_yes() {
  if [[ "${NEXUS_ZNETWORK_NO_SUDO:-0}" != "1" ]]; then
    nexus_znetwork_pol_root_gate || return 1
  fi
  nexus_znetwork_retire_legacy_handlers || true
  nexus_znetwork_replace_connection || true
  nexus_znetwork_activate_log "operator_accept" "OK" "choice=yes mode=${ZNETWORK_MODE} underhook=${ZNETWORK_UNDERHOOK:-0}"

  # Prefer v2 orchestrator (truth gate + sovereign time + tray swap).
  if nexus_znetwork_orchestrator_py activate --elevated >/dev/null 2>&1; then
    nexus_znetwork_activate_log "orchestrator" "OK" "v2_activate"
    nexus_znetwork_ensure_tray || true
    nexus_znetwork_activate_log "complete" "OK" "running=true swap=tray_and_bridges"
    return 0
  fi

  nexus_znetwork_triple_check || {
    nexus_znetwork_activate_log "complete" "FAIL" "triple_check"
    return 1
  }
  nexus_znetwork_activate_log "triple_check" "OK" "mode=${ZNETWORK_MODE}"

  nexus_znetwork_user_attach || true
  nexus_znetwork_mark_running
  nexus_znetwork_tray_swap || true
  nexus_znetwork_activate_log "complete" "OK" "running=true swap=tray_legacy_path"
  return 0
}

# ZNetwork with us — relayer owns sole internet in/out stack.
nexus_znetwork_startup_with_us() {
  nexus_znetwork_ensure_host_network || true
  nexus_znetwork_relayer_board
  nexus_znetwork_install_autostart 2>/dev/null || true
}

# Legacy alias — ZNetwork is ingrained; always auto-activate (no zenity Yes/No/Skip).
nexus_znetwork_startup_prompt() {
  nexus_znetwork_startup_with_us
}

nexus_znetwork_triple_check() {
  if [[ "${ZNETWORK_FAST:-0}" != "1" ]] \
    && timeout 12 nexus_znetwork_orchestrator_py triple-check >/dev/null 2>&1; then
    nexus_log "INFO" "znetwork" "TRIPLE_CHECK_OK mode=${ZNETWORK_MODE} via=orchestrator"
    return 0
  fi

  local bin probe_ok=0 status_ok=0 gate_ok=0 gate_script out="${NEXUS_STATE_DIR}/znetwork-status.json"
  bin="$(nexus_znetwork_bin)" || {
    nexus_log "WARN" "znetwork" "BINARY_MISSING path=${ZNETWORK_BIN}"
    return 1
  }
  export SG_ROOT="${SG_ROOT:-$(cd "${NEXUS_INSTALL_ROOT}/.." 2>/dev/null && pwd)}"
  export ZNETWORK_MODE="${ZNETWORK_MODE}"
  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true

  if "${bin}" probe --json >/dev/null 2>&1; then
    probe_ok=1
  fi
  if "${bin}" status --json >"${out}.tmp" 2>/dev/null; then
    status_ok=1
    mv -f "${out}.tmp" "${out}" 2>/dev/null || cp "${out}.tmp" "${out}" 2>/dev/null || true
    rm -f "${out}.tmp" 2>/dev/null || true
  else
    rm -f "${out}.tmp" 2>/dev/null || true
  fi
  if nexus_znetwork_protection_only; then
    gate_ok=1
  elif [[ "${ZNETWORK_MODE:-}" == "ACTIVE" ]] \
    || [[ "${ZNETWORK_NO_REVIEW:-0}" == "1" ]] \
    || [[ "${ZNETWORK_REVIEW_APPROVED:-0}" == "1" ]] \
    || [[ "${ZNETWORK_OUTSIDE_LAB:-0}" == "1" ]]; then
    gate_ok=1
  else
    gate_script="$(nexus_znetwork_review_gate_script 2>/dev/null || true)"
    if [[ -n "$gate_script" ]]; then
      ZNETWORK_BIN="${bin}" SG_ROOT="${SG_ROOT}" ZNETWORK_MODE="${ZNETWORK_MODE}" \
        NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
        ZNETWORK_NO_REVIEW="${ZNETWORK_NO_REVIEW:-1}" \
        ZNETWORK_REVIEW_APPROVED="${ZNETWORK_REVIEW_APPROVED:-1}" \
        "$gate_script" >/dev/null 2>&1 && gate_ok=1
    fi
  fi

  if [[ "$probe_ok" -eq 1 && "$status_ok" -eq 1 && "$gate_ok" -eq 1 ]]; then
    nexus_log "INFO" "znetwork" "TRIPLE_CHECK_OK mode=${ZNETWORK_MODE} ready=REVIEW"
    return 0
  fi
  nexus_log "WARN" "znetwork" "TRIPLE_CHECK_FAIL probe=${probe_ok} status=${status_ok} gate=${gate_ok}"
  return 1
}

nexus_znetwork_publish_quiet() {
  # Plate meld / vigil — witness only; never slam relayer or drop links.
  [[ "${NEXUS_ZNETWORK:-1}" == "1" ]] || return 0
  local out="${NEXUS_STATE_DIR}/znetwork-status.json" size=0
  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true
  if [[ -f "$out" ]]; then
    size="$(stat -c%s "$out" 2>/dev/null || echo 0)"
  fi
  if [[ "$size" -lt 32 ]]; then
    nexus_znetwork_triple_check_fast 2>/dev/null || true
  fi
  if nexus_znetwork_is_running && nexus_znetwork_relayer; then
    nexus_znetwork_relayer_watch || true
  fi
  if [[ "${ZNETWORK_DEFER_TRAY:-0}" == "1" ]]; then
    nexus_znetwork_tray_silent 2>/dev/null || true
  else
    nexus_znetwork_ensure_tray 2>/dev/null || true
  fi
  return 0
}

nexus_znetwork_publish() {
  [[ "${NEXUS_ZNETWORK:-1}" == "1" ]] || return 0
  if [[ "${ZNETWORK_PUBLISH_QUIET:-0}" == "1" ]] \
    || { nexus_znetwork_relayer && nexus_znetwork_relayer_already_active; }; then
    nexus_znetwork_publish_quiet
    return 0
  fi
  nexus_znetwork_triple_check || return 1
  if nexus_znetwork_is_running && ! nexus_znetwork_protection_only; then
    if nexus_znetwork_relayer; then
      nexus_znetwork_relayer_watch || true
    else
      nexus_znetwork_exploit_scan || true
      nexus_znetwork_hostile_scan || true
      nexus_znetwork_hostile_respond || true
    fi
  fi
  nexus_znetwork_ensure_tray 2>/dev/null || true
}

nexus_znetwork_build() {
  [[ -d "${NEXUS_INSTALL_ROOT}/ZNetwork" ]] || return 1
  command -v cmake >/dev/null 2>&1 || return 1
  (
    cd "${NEXUS_INSTALL_ROOT}/ZNetwork"
    cmake -B build -DCMAKE_BUILD_TYPE=Release >/dev/null 2>&1
    cmake --build build >/dev/null 2>&1
  ) && nexus_znetwork_bin >/dev/null 2>&1
}

nexus_znetwork_activate() {
  export ZNETWORK_MODE="${ZNETWORK_MODE:-ACTIVE}"
  export ZNETWORK_SMART_INSIDE=1
  export ZNETWORK_PROTECTION_ONLY=0
  export ZNETWORK_TAKEOVER=0
  export ZNETWORK_REVIEW_APPROVED="${ZNETWORK_REVIEW_APPROVED:-1}"
  export ZNETWORK_LAB_GATE_OK="${ZNETWORK_LAB_GATE_OK:-1}"
  export ZNETWORK_NO_REVIEW="${ZNETWORK_NO_REVIEW:-1}"
  export ZNETWORK_FORCE_REBOARD=1
  export NEXUS_ZNETWORK_NO_SUDO="${NEXUS_ZNETWORK_NO_SUDO:-0}"
  export ZNETWORK_NEVER_HARM_OS=1
  export NEXUS_NEVER_HARM_OS=1
  nexus_znetwork_relayer_py relay --force 2>/dev/null || nexus_znetwork_replace_py replace --force || nexus_znetwork_startup_with_us
}

nexus_znetwork_status_line() {
  local out="${NEXUS_STATE_DIR}/znetwork-status.json"
  if nexus_znetwork_is_running; then
    printf 'znetwork=running'
    [[ -f "$out" ]] && printf ' status=%s' "$out"
    printf '\n'
  elif [[ -f "$out" ]]; then
    printf 'znetwork=ready file=%s\n' "$out"
  elif nexus_znetwork_bin >/dev/null 2>&1; then
    printf 'znetwork=binary_ok status=pending\n'
  else
    printf 'znetwork=missing\n'
  fi
}