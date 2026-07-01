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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/queen-layer-boot.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Queen layer boot — :9481 world daemon + host desktop refresh; survives reboot.

nexus_queen_root() {
  if [[ -n "${QUEEN_ROOT:-}" && -d "${QUEEN_ROOT}" ]]; then
    printf '%s' "${QUEEN_ROOT}"
    return 0
  fi
  if declare -f sg_paths_queen_root >/dev/null 2>&1; then
    printf '%s' "$(sg_paths_queen_root)"
    return 0
  fi
  printf '%s' "${NEXUS_INSTALL_ROOT}/Queen"
}

nexus_queen_world_port() {
  printf '%s' "${QUEEN_WORLD_PORT:-9481}"
}

nexus_queen_world_url() {
  local host="${QUEEN_WORLD_HOST:-127.0.0.1}"
  local port
  port="$(nexus_queen_world_port)"
  printf 'http://%s:%s/world/browser.html' "$host" "$port"
}

nexus_queen_world_listening() {
  local host="${QUEEN_WORLD_HOST:-127.0.0.1}"
  local port py pythong_bin
  port="$(nexus_queen_world_port)"
  py="$(nexus_queen_root)/lib/queen-world.py"
  [[ -f "$py" ]] || return 1
  pythong_bin="${NEXUS_PYTHONG:-$(nexus_resolve_pythong 2>/dev/null || true)}"
  [[ -n "$pythong_bin" ]] || return 1
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    QUEEN_ROOT="$(nexus_queen_root)" QUEEN_WORLD_HOST="$host" QUEEN_WORLD_PORT="$port" \
    "$pythong_bin" "$py" --check 2>/dev/null
}

nexus_queen_layer_record() {
  local ts
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)"
  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true
  cat >"${NEXUS_STATE_DIR}/queen-layer.last" <<EOF
ts=${ts}
state_dir=${NEXUS_STATE_DIR}
world_port=$(nexus_queen_world_port)
world_url=$(nexus_queen_world_url)
install_root=${NEXUS_INSTALL_ROOT}
EOF
  chmod 640 "${NEXUS_STATE_DIR}/queen-layer.last" 2>/dev/null || true
}

nexus_queen_world_ensure() {
  [[ "${NEXUS_QUEEN_WORLD_BOOT:-1}" == "1" ]] || return 0
  local queen_root py pythong_bin host port log
  queen_root="$(nexus_queen_root)"
  py="${queen_root}/lib/queen-world.py"
  [[ -f "$py" ]] || {
    nexus_log "WARN" "queen-layer" "WORLD_SCRIPT_MISSING path=${py}"
    return 1
  }
  pythong_bin="${NEXUS_PYTHONG:-$(nexus_resolve_pythong 2>/dev/null || true)}"
  [[ -n "$pythong_bin" ]] || {
    nexus_log "WARN" "queen-layer" "PYTHONG_MISSING"
    return 1
  }
  host="${QUEEN_WORLD_HOST:-127.0.0.1}"
  port="$(nexus_queen_world_port)"
  log="${NEXUS_STATE_DIR}/queen-world.log"

  if nexus_queen_world_listening; then
    nexus_log "INFO" "queen-layer" "WORLD_ALREADY port=${port}"
    nexus_queen_layer_record
    return 0
  fi

  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true
  nohup env \
    NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
    NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    SG_ROOT="${SG_ROOT:-}" \
    QUEEN_ROOT="${queen_root}" \
    QUEEN_WORLD_HOST="${host}" \
    QUEEN_WORLD_PORT="${port}" \
    QUEEN_SOVEREIGN=1 \
    NEXUS_QUEEN_SOVEREIGN=1 \
    PATH="${PATH}" \
    "$pythong_bin" "$py" --daemon >>"$log" 2>&1 || true

  local _
  for _ in $(seq 1 30); do
    if nexus_queen_world_listening; then
      nexus_log "INFO" "queen-layer" "WORLD_STARTED port=${port} url=$(nexus_queen_world_url)"
      nexus_queen_layer_record
      return 0
    fi
    sleep 0.2
  done
  nexus_log "WARN" "queen-layer" "WORLD_START_TIMEOUT port=${port} log=${log}"
  return 1
}

nexus_queen_host_desktop_refresh() {
  [[ "${NEXUS_HOST_DESKTOP_BOOT_REFRESH:-1}" == "1" ]] || return 0
  local script pythong_bin
  script="${NEXUS_INSTALL_ROOT}/lib/field-host-desktop.py"
  [[ -f "$script" ]] || return 0
  pythong_bin="${NEXUS_PYTHONG:-$(nexus_resolve_pythong 2>/dev/null || true)}"
  [[ -n "$pythong_bin" ]] || return 0
  if NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    NEXUS_HOST_DESKTOP_REFRESH=1 \
    "$pythong_bin" "$script" build >/dev/null 2>&1; then
    nexus_log "INFO" "queen-layer" "HOST_DESKTOP_REFRESH ok"
    return 0
  fi
  nexus_log "WARN" "queen-layer" "HOST_DESKTOP_REFRESH deferred"
  return 1
}

nexus_queen_icon_refresh() {
  local kit pythong_bin
  kit="$(nexus_queen_root)/scripts/queen-icon-kit.py"
  [[ -f "$kit" ]] || return 0
  pythong_bin="${NEXUS_PYTHONG:-$(nexus_resolve_pythong 2>/dev/null || true)}"
  [[ -n "$pythong_bin" ]] || return 0
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    "$pythong_bin" "$kit" >/dev/null 2>&1 || true
}

nexus_queen_layer_refresh() {
  nexus_queen_world_ensure || true
  nexus_queen_host_desktop_refresh || true
  nexus_queen_icon_refresh || true
  nexus_queen_layer_record
}

nexus_queen_layer_install_autostart() {
  local home autostart desktop
  home="${HOME:-}"
  [[ -n "$home" ]] || return 0
  autostart="${home}/.config/autostart"
  desktop="${autostart}/nexus-queen-world.desktop"
  if [[ "${NEXUS_BOOT_C2_ONLY:-1}" == "1" ]] || [[ "${NEXUS_QUEEN_LAYER_AUTOSTART:-0}" != "1" ]]; then
    rm -f "$desktop" 2>/dev/null || true
    nexus_log "INFO" "queen-layer" "AUTOSTART_SKIP c2_only boot=${NEXUS_BOOT_C2_ONLY:-1}"
    return 0
  fi
  [[ -n "${DISPLAY:-}" || -n "${WAYLAND_DISPLAY:-}" ]] || return 0
  local root state_dir
  root="${NEXUS_INSTALL_ROOT}"
  state_dir="${NEXUS_STATE_DIR}"
  mkdir -p "$autostart" 2>/dev/null || return 0
  cat >"$desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Queen World Layer
Comment=Queen browser shell on :9481 — field layer persists across reboot
Icon=queen-browser
Exec=env NEXUS_INSTALL_ROOT=${root} NEXUS_FIELD_STANDALONE=1 DISPLAY=:0 bash -c 'source ${root}/lib/nexus-common.sh; nexus_init_runtime_paths; source ${root}/lib/queen-layer-boot.sh; nexus_queen_layer_refresh'
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
StartupNotify=false
EOF
  chmod 644 "$desktop" 2>/dev/null || true
  nexus_log "INFO" "queen-layer" "AUTOSTART installed ${desktop} state=${state_dir}"
}