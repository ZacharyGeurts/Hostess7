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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/panel-tray.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS panel system tray — taskbar icon; click opens fast-track tab picker.

nexus_panel_tray_python() {
  local py=""
  if declare -f nexus_resolve_tray_python >/dev/null 2>&1; then
    py="$(nexus_resolve_tray_python 2>/dev/null || true)"
  fi
  if [[ -z "$py" ]]; then
    py="$(command -v python3 2>/dev/null || true)"
  fi
  [[ -n "$py" ]] && printf '%s' "$py"
}

nexus_panel_tray_mode() {
  if [[ "${NEXUS_TRAY_MODE:-}" == "znetwork" ]]; then
    printf 'znetwork'
    return 0
  fi
  if [[ -f "${NEXUS_STATE_DIR}/znetwork-tray-mode.json" ]] \
    && grep -q '"mode"[[:space:]]*:[[:space:]]*"znetwork"' "${NEXUS_STATE_DIR}/znetwork-tray-mode.json" 2>/dev/null \
    && grep -q '"active"[[:space:]]*:[[:space:]]*true' "${NEXUS_STATE_DIR}/znetwork-tray-mode.json" 2>/dev/null; then
    printf 'znetwork'
    return 0
  fi
  if [[ -f "${NEXUS_STATE_DIR}/znetwork-operator.json" ]]; then
    grep -q '"choice"[[:space:]]*:[[:space:]]*"yes"' "${NEXUS_STATE_DIR}/znetwork-operator.json" 2>/dev/null \
      && grep -q '"running"[[:space:]]*:[[:space:]]*true' "${NEXUS_STATE_DIR}/znetwork-operator.json" 2>/dev/null \
      && { printf 'znetwork'; return 0; }
  fi
  printf 'nexus'
}

nexus_panel_tray_icon_path() {
  local mode state_icon
  mode="$(nexus_panel_tray_mode)"
  if [[ "$mode" == "znetwork" ]]; then
    state_icon="${NEXUS_STATE_DIR}/znetwork-tray.png"
  else
    state_icon="${NEXUS_STATE_DIR}/nexus-tray.png"
  fi
  local tray_py
  tray_py="$(nexus_panel_tray_python)"
  if [[ -n "$tray_py" && -x "$tray_py" ]] && [[ -f "${NEXUS_INSTALL_ROOT}/lib/panel-tray-icon.py" ]]; then
    NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      NEXUS_TRAY_MODE="${mode}" NEXUS_TRAY_ICON_REFRESH="${NEXUS_TRAY_ICON_REFRESH:-0}" \
      "$tray_py" "${NEXUS_INSTALL_ROOT}/lib/panel-tray-icon.py" >/dev/null 2>&1 || true
  fi
  if [[ -s "$state_icon" ]]; then
    printf '%s' "$state_icon"
    return 0
  fi
  local candidate
  if [[ "$mode" == "znetwork" ]]; then
    for candidate in \
      "${NEXUS_INSTALL_ROOT}/panel/assets/znetwork-tray-24.png" \
      "${NEXUS_INSTALL_ROOT}/panel/assets/znetwork-tray-32.png" \
      "${NEXUS_INSTALL_ROOT}/panel/assets/znetwork-tray-22.png"; do
      if [[ -s "$candidate" ]]; then
        printf '%s' "$candidate"
        return 0
      fi
    done
  else
    for candidate in \
      "${NEXUS_INSTALL_ROOT}/panel/assets/queen-tray-24.png" \
      "${NEXUS_INSTALL_ROOT}/panel/assets/nexus-field-24.png" \
      "${NEXUS_INSTALL_ROOT}/panel/assets/nexus-tray-us-24.png" \
      "${NEXUS_INSTALL_ROOT}/panel/assets/nexus-field.png" \
      "${NEXUS_INSTALL_ROOT}/assets/nexus-field.png" \
      "${NEXUS_INSTALL_ROOT}/panel/assets/nexus-tray-us.png" \
      "${NEXUS_INSTALL_ROOT}/panel/assets/nexus-shield.png" \
      "${NEXUS_INSTALL_ROOT}/assets/nexus-shield.png"; do
      if [[ -s "$candidate" ]]; then
        printf '%s' "$candidate"
        return 0
      fi
    done
  fi
}

nexus_panel_tray_icon_refresh() {
  rm -f \
    "${NEXUS_STATE_DIR}/nexus-tray.png" \
    "${NEXUS_STATE_DIR}/nexus-tray-icon.stamp" \
    "${NEXUS_STATE_DIR}/znetwork-tray.png" \
    "${NEXUS_STATE_DIR}/znetwork-tray-icon.stamp" \
    2>/dev/null || true
  nexus_panel_tray_icon_path >/dev/null 2>&1 || true
}

# After ZNetwork password/activate — swap taskbar icon + restart tray in znetwork mode.
nexus_panel_tray_znetwork_swap() {
  [[ "${NEXUS_PANEL_TRAY:-1}" == "1" ]] || return 0
  local mode="${NEXUS_TRAY_MODE:-znetwork}"
  local mode_file="${NEXUS_STATE_DIR}/znetwork-tray-mode.json"
  export NEXUS_TRAY_MODE="$mode"
  export NEXUS_TRAY_ICON_REFRESH=1
  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true
  if [[ "$mode" == "znetwork" ]]; then
    printf '{"schema":"znetwork-tray-mode/v2","mode":"znetwork","app_id":"znetwork-field-panel","icon":"znetwork-tray","active":true,"title":"ZNetwork Relayer","swapped_at":"%s"}\n' \
      "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >"$mode_file" 2>/dev/null || true
  else
    printf '{"schema":"znetwork-tray-mode/v2","mode":"nexus","active":false,"reverted_at":"%s"}\n' \
      "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >"$mode_file" 2>/dev/null || true
  fi
  nexus_panel_tray_icon_refresh
  # Soft restart — keep watchdog alive so the tray does not vanish mid-swap.
  nexus_panel_tray_stop_app 2>/dev/null || true
  sleep 0.3
  nexus_panel_tray_start 2>/dev/null || true
  nexus_panel_tray_watchdog_start 2>/dev/null || true
  nexus_log "INFO" "panel-tray" "ZNETWORK_TRAY_SWAP mode=${mode}"
}

# True only when pid is a live python/pythong panel-tray.py daemon (not bash/grep wrappers).
nexus_panel_tray_pid_valid() {
  local pid="$1" cmdline=""
  [[ -n "$pid" && "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  if [[ -r "/proc/${pid}/cmdline" ]]; then
    cmdline="$(tr '\0' ' ' <"/proc/${pid}/cmdline" 2>/dev/null || true)"
  fi
  [[ -n "$cmdline" ]] || return 1
  [[ "$cmdline" == *panel-tray.py* ]] || return 1
  [[ "$cmdline" == *"panel-tray.py open"* ]] && return 1
  [[ "$cmdline" == *python* ]] || return 1
  return 0
}

# PIDs of long-running tray daemons (exclude short-lived `open` helper).
nexus_panel_tray_pids() {
  local pid
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    nexus_panel_tray_pid_valid "$pid" && printf '%s\n' "$pid"
  done < <(pgrep -f "panel-tray\.py" 2>/dev/null || true)
}

nexus_panel_tray_clear_stale_state() {
  local pid_file="${NEXUS_STATE_DIR}/panel-tray.pid"
  local lock_file="${NEXUS_STATE_DIR}/panel-tray.lock"
  local old=""
  if [[ -f "$pid_file" ]]; then
    old="$(cat "$pid_file" 2>/dev/null || true)"
    if [[ -z "$old" ]] || ! nexus_panel_tray_pid_valid "$old"; then
      rm -f "$pid_file" "$lock_file" 2>/dev/null || true
    fi
  fi
}

nexus_panel_tray_is_running() {
  local pid
  while IFS= read -r pid; do
    [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null && return 0
  done < <(nexus_panel_tray_pids)
  return 1
}

nexus_panel_tray_prune_duplicates() {
  local keep_pid="${1:-}"
  local pid_file="${NEXUS_STATE_DIR}/panel-tray.pid"
  local -a pids=()
  mapfile -t pids < <(nexus_panel_tray_pids)
  if [[ ${#pids[@]} -eq 0 ]]; then
    if [[ -n "$keep_pid" ]] && kill -0 "$keep_pid" 2>/dev/null; then
      printf '%s\n' "$keep_pid" >"$pid_file" 2>/dev/null || true
      return 0
    fi
    rm -f "$pid_file" 2>/dev/null || true
    return 0
  fi
  if [[ -z "$keep_pid" ]]; then
    keep_pid="$(cat "$pid_file" 2>/dev/null || true)"
  fi
  if [[ -n "$keep_pid" ]] && ! kill -0 "$keep_pid" 2>/dev/null; then
    keep_pid=""
  fi
  if [[ -z "$keep_pid" ]]; then
    keep_pid="${pids[0]}"
  fi
  for pid in "${pids[@]}"; do
    [[ "$pid" == "$keep_pid" ]] && continue
    kill "$pid" 2>/dev/null || true
    sleep 0.1
    kill -9 "$pid" 2>/dev/null || true
  done
  printf '%s\n' "$keep_pid" >"$pid_file" 2>/dev/null || true
}

nexus_panel_tray_watchdog_pid_valid() {
  local pid="$1" cmdline=""
  [[ -n "$pid" && "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  if [[ -r "/proc/${pid}/comm" ]]; then
    read -r cmdline <"/proc/${pid}/comm" 2>/dev/null || true
    [[ "$cmdline" == "nexus-panel-tray-watchdog" ]] && return 0
  fi
  if [[ -r "/proc/${pid}/cmdline" ]]; then
    cmdline="$(tr '\0' ' ' <"/proc/${pid}/cmdline" 2>/dev/null || true)"
    [[ "$cmdline" == *nexus-panel-tray-watchdog* ]] && return 0
    [[ "$cmdline" == *panel-tray-watchdog.pid* ]] \
      && [[ "$cmdline" == *nexus_panel_tray_start* ]] && return 0
  fi
  return 1
}

nexus_panel_tray_watchdog_pids() {
  local pid
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    nexus_panel_tray_watchdog_pid_valid "$pid" && printf '%s\n' "$pid"
  done < <(pgrep -f 'nexus-panel-tray-watchdog' 2>/dev/null || true)
}

nexus_panel_tray_watchdog_prune() {
  local keep_pid="${1:-}"
  local wd_pid="${NEXUS_STATE_DIR}/panel-tray-watchdog.pid"
  local -a pids=()
  mapfile -t pids < <(nexus_panel_tray_watchdog_pids)
  if [[ ${#pids[@]} -eq 0 ]]; then
    rm -f "$wd_pid" 2>/dev/null || true
    return 0
  fi
  if [[ -z "$keep_pid" ]]; then
    keep_pid="$(cat "$wd_pid" 2>/dev/null || true)"
  fi
  if [[ -n "$keep_pid" ]] && ! nexus_panel_tray_watchdog_pid_valid "$keep_pid"; then
    keep_pid=""
  fi
  if [[ -z "$keep_pid" ]]; then
    keep_pid="${pids[0]}"
  fi
  for pid in "${pids[@]}"; do
    [[ "$pid" == "$keep_pid" ]] && continue
    kill "$pid" 2>/dev/null || true
    sleep 0.1
    kill -9 "$pid" 2>/dev/null || true
  done
  printf '%s\n' "$keep_pid" >"$wd_pid" 2>/dev/null || true
}

nexus_panel_tray_start() {
  [[ "${NEXUS_PANEL_TRAY:-1}" == "1" ]] || return 0
  local script="${NEXUS_INSTALL_ROOT}/lib/panel-tray.py"
  local tray_py
  [[ -f "$script" ]] || return 0
  tray_py="$(nexus_panel_tray_python)"
  [[ -n "$tray_py" && -x "$tray_py" ]] || return 0
  [[ -n "${DISPLAY:-}" || -n "${WAYLAND_DISPLAY:-}" ]] || return 0

  local start_lock="${NEXUS_STATE_DIR}/panel-tray.start.lock"
  (
    flock -n 9 || {
      nexus_log "INFO" "panel-tray" "TRAY_START_SKIPPED flock_busy"
      exit 0
    }
    nexus_panel_tray_clear_stale_state
    nexus_panel_tray_icon_refresh
    nexus_panel_tray_prune_duplicates ""

    if nexus_panel_tray_is_running; then
      local old_pid
      old_pid="$(cat "${NEXUS_STATE_DIR}/panel-tray.pid" 2>/dev/null || true)"
      nexus_log "INFO" "panel-tray" "TRAY_ALREADY_RUNNING pid=${old_pid}"
      exit 0
    fi

    local pid_file="${NEXUS_STATE_DIR}/panel-tray.pid"
    local tray_log="${NEXUS_STATE_DIR}/panel-tray.log"
    {
      printf '[%s] TRAY_SPAWN py=%s mode=%s display=%s\n' \
        "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$tray_py" "$(nexus_panel_tray_mode)" "${DISPLAY:-:0}"
    } >>"$tray_log" 2>/dev/null || true
    nohup env \
      NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
      NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      NEXUS_THREAT_PANEL_PORT="${NEXUS_THREAT_PANEL_PORT:-9477}" \
      NEXUS_TRAY_MODE="$(nexus_panel_tray_mode)" \
      NEXUS_TRAY_ICON_REFRESH=1 \
      DISPLAY="${DISPLAY:-:0}" \
      DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$(id -u)/bus}" \
      XDG_CURRENT_DESKTOP="${XDG_CURRENT_DESKTOP:-}" \
      "$tray_py" "$script" >>"$tray_log" 2>&1 &
    local pid=$!
    printf '%s\n' "$pid" >"$pid_file" 2>/dev/null || true
    sleep 1
    nexus_panel_tray_prune_duplicates "$pid"
    if kill -0 "$pid" 2>/dev/null; then
      nexus_log "INFO" "panel-tray" "TRAY_STARTED pid=${pid} port=${NEXUS_THREAT_PANEL_PORT:-9477}"
      echo "NEXUS tray icon active — click near the clock to pick a panel tab."
      exit 0
    fi
    nexus_log "WARN" "panel-tray" "TRAY_START_FAILED see ${NEXUS_STATE_DIR}/panel-tray.log"
    exit 1
  ) 9>"$start_lock"
}

nexus_panel_tray_stop_app() {
  local pid
  for pid in $(nexus_panel_tray_pids); do
    kill "$pid" 2>/dev/null || true
    sleep 0.1
    kill -9 "$pid" 2>/dev/null || true
  done
  pkill -f "${NEXUS_INSTALL_ROOT}/lib/panel-tray.py" 2>/dev/null || pkill -f "panel-tray.py" 2>/dev/null || true
  rm -f \
    "${NEXUS_STATE_DIR}/panel-tray.pid" \
    "${NEXUS_STATE_DIR}/panel-tray.lock" \
    "${NEXUS_STATE_DIR}/panel-tray.start.lock" \
    2>/dev/null || true
}

nexus_panel_tray_stop() {
  nexus_panel_tray_stop_app
  for pid in $(nexus_panel_tray_watchdog_pids); do
    kill "$pid" 2>/dev/null || true
    kill -9 "$pid" 2>/dev/null || true
  done
  pkill -f "nexus-panel-tray-watchdog" 2>/dev/null || true
  rm -f \
    "${NEXUS_STATE_DIR}/panel-tray-watchdog.pid" \
    "${NEXUS_STATE_DIR}/panel-tray-watchdog.lock" \
    2>/dev/null || true
}

nexus_panel_tray_watchdog_start() {
  [[ "${NEXUS_PANEL_TRAY:-1}" == "1" ]] || return 0
  [[ -n "${DISPLAY:-}" || -n "${WAYLAND_DISPLAY:-}" ]] || return 0
  local wd_lock="${NEXUS_STATE_DIR}/panel-tray-watchdog.lock"
  local wd_pid="${NEXUS_STATE_DIR}/panel-tray-watchdog.pid"
  nexus_panel_tray_watchdog_reconcile 2>/dev/null || true
  (
    flock -n 9 || exit 0
    if [[ -f "$wd_pid" ]]; then
      local old
      old="$(cat "$wd_pid" 2>/dev/null || true)"
      if nexus_panel_tray_watchdog_pid_valid "$old"; then
        exit 0
      fi
    fi
    nexus_panel_tray_watchdog_prune ""
    local wd_log="${NEXUS_STATE_DIR}/panel-tray-watchdog.log"
    nohup env \
      NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
      NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      NEXUS_THREAT_PANEL_PORT="${NEXUS_THREAT_PANEL_PORT:-9477}" \
      DISPLAY="${DISPLAY:-:0}" \
      DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=/run/user/$(id -u)/bus}" \
      WD_PID_FILE="${wd_pid}" \
      bash -s >>"$wd_log" 2>&1 <<'WATCHDOG_LOOP' &
exec -a nexus-panel-tray-watchdog bash -c '
printf "%s\n" "$$" > "$WD_PID_FILE"
while true; do
  if ! source "$NEXUS_INSTALL_ROOT/lib/nexus-common.sh" 2>/dev/null; then
    sleep 20
    continue
  fi
  # shellcheck source=/dev/null
  source "$NEXUS_INSTALL_ROOT/lib/panel-tray.sh"
  nexus_panel_tray_watchdog_prune "$$"
  if ! nexus_panel_tray_is_running; then
    nexus_panel_tray_start >/dev/null 2>&1 || true
  else
    nexus_panel_tray_prune_duplicates "$(cat "$NEXUS_STATE_DIR/panel-tray.pid" 2>/dev/null || true)"
  fi
  sleep 15
done
'
WATCHDOG_LOOP
    local new_pid=$!
    printf '%s\n' "$new_pid" >"$wd_pid" 2>/dev/null || true
    sleep 0.3
    nexus_panel_tray_watchdog_prune "$new_pid"
  ) 9>"$wd_lock"
}

# Single entry: prune duplicates, one tray, one watchdog.
nexus_panel_tray_ensure_once() {
  nexus_panel_tray_clear_stale_state
  nexus_panel_tray_prune_duplicates ""
  if ! nexus_panel_tray_is_running; then
    nexus_panel_tray_start 2>/dev/null || true
  fi
  nexus_panel_tray_watchdog_reconcile 2>/dev/null || true
  nexus_panel_tray_watchdog_start 2>/dev/null || true
}

# Login autostart — honor active ZNetwork tray mode after reboot.
nexus_panel_tray_autostart_bootstrap() {
  nexus_panel_tray_clear_stale_state
  nexus_panel_tray_watchdog_reconcile 2>/dev/null || true
  nexus_panel_tray_icon_refresh 2>/dev/null || true
  if [[ "$(nexus_panel_tray_mode)" == "znetwork" ]]; then
    export NEXUS_TRAY_MODE=znetwork
    export NEXUS_TRAY_ICON_REFRESH=1
    nexus_panel_tray_znetwork_swap 2>/dev/null \
      || nexus_panel_tray_ensure_once 2>/dev/null || true
  else
    nexus_panel_tray_ensure_once 2>/dev/null || true
  fi
}

nexus_panel_tray_watchdog_reconcile() {
  local wd_pid="${NEXUS_STATE_DIR}/panel-tray-watchdog.pid"
  local -a pids=()
  mapfile -t pids < <(nexus_panel_tray_watchdog_pids)
  if [[ ${#pids[@]} -eq 0 ]]; then
    rm -f "$wd_pid" 2>/dev/null || true
    return 0
  fi
  nexus_panel_tray_watchdog_prune "$(cat "$wd_pid" 2>/dev/null || echo "${pids[0]}")"
}

nexus_panel_tray_install_autostart() {
  [[ -n "${DISPLAY:-}" || -n "${WAYLAND_DISPLAY:-}" ]] || return 0
  local home="${HOME:-/home/default}"
  local autostart="${home}/.config/autostart"
  local root="${NEXUS_INSTALL_ROOT}"
  local state="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}"
  local sg_root="${SG_ROOT:-}"
  local desktop="${autostart}/nexus-panel-tray.desktop"
  local tray_mode="znetwork"
  if [[ -z "$sg_root" || "$sg_root" == "$root" ]]; then
    sg_root="$(cd "${root}/.." 2>/dev/null && pwd)"
  fi
  if [[ "$(nexus_panel_tray_mode 2>/dev/null || echo nexus)" != "znetwork" ]]; then
    tray_mode="nexus"
  fi
  mkdir -p "$autostart" 2>/dev/null || return 0
  cat >"$desktop" <<EOF
[Desktop Entry]
Type=Application
Name=ZNetwork Field Tray
Comment=ZNetwork taskbar icon — fast tab picker when relayer is active
Icon=network-workgroup
Exec=env SG_ROOT=${sg_root} NEXUS_INSTALL_ROOT=${root} NEXUS_STATE_DIR=${state} NEXUS_TRAY_MODE=znetwork ZNETWORK_DEFER_TRAY=0 ZNETWORK_MODE=ACTIVE DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus bash -c 'source ${root}/lib/nexus-common.sh; source ${root}/lib/znetwork-field.sh; source ${root}/lib/panel-tray.sh; nexus_znetwork_ensure_tray 2>/dev/null || nexus_panel_tray_autostart_bootstrap'
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=3
StartupNotify=false
EOF
  chmod 644 "$desktop" 2>/dev/null || true
  nexus_log "INFO" "panel-tray" "AUTOSTART installed ${desktop} mode=${tray_mode}"
}

nexus_panel_open_tab() {
  local route="${1:-command}"
  local script="${NEXUS_INSTALL_ROOT}/lib/panel-tray.py"
  local tray_py
  tray_py="$(nexus_panel_tray_python)"
  if [[ -f "$script" && -n "$tray_py" && -x "$tray_py" ]]; then
    NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
    NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    NEXUS_THREAT_PANEL_PORT="${NEXUS_THREAT_PANEL_PORT:-9477}" \

    DISPLAY="${DISPLAY:-:0}" \
      "$tray_py" "$script" open "$route" 2>/dev/null && return 0
  fi
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
  QUEEN_ROOT="${QUEEN_ROOT:-${NEXUS_INSTALL_ROOT}/Queen}" \
  NEXUS_THREAT_PANEL_PORT="${NEXUS_THREAT_PANEL_PORT:-9477}" \
  QUEEN_WORLD_PORT="${QUEEN_WORLD_PORT:-9481}" \
    pythong "${NEXUS_INSTALL_ROOT}/lib/queen-panel-open.py" nexus "$route" >/dev/null 2>&1 &
}