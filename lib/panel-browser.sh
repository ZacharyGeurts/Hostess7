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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/panel-browser.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Panel browser — Queen hardened shell only. NEXUS opens as a Queen tab, never Firefox/Chrome.

nexus_panel_url() {
  local port="${NEXUS_THREAT_PANEL_PORT:-9477}"
  printf 'http://127.0.0.1:%s/field' "$port"
}

nexus_panel_app_url() {
  local port="${NEXUS_THREAT_PANEL_PORT:-9477}"
  printf 'http://127.0.0.1:%s/app' "$port"
}

nexus_panel_tristate_url() {
  local port="${NEXUS_THREAT_PANEL_PORT:-9477}"
  printf 'http://127.0.0.1:%s/tristate-installer' "$port"
}

nexus_panel_desired_version() {
  local common="${NEXUS_INSTALL_ROOT}/lib/nexus-common.sh"
  [[ -f "$common" ]] || return 1
  grep -o 'NEXUS_VERSION="[^"]*"' "$common" 2>/dev/null | head -1 | cut -d'"' -f2
}

nexus_panel_served_version() {
  local port="${NEXUS_THREAT_PANEL_PORT:-9477}"
  local html
  html="$(curl -s --connect-timeout 2 "http://127.0.0.1:${port}/field" 2>/dev/null)" || return 1
  [[ -n "$html" ]] || return 1
  if grep -q 'underlay-f9' <<<"$html" 2>/dev/null; then
    grep -oE 'NEXUS-Shield v[0-9]+\.[0-9]+\.[0-9]+' <<<"$html" 2>/dev/null | head -1 | sed 's/.*v//' && return 0
  fi
  grep -oE 'NEXUS-Shield v[0-9]+\.[0-9]+\.[0-9]+' <<<"$html" 2>/dev/null | head -1 | sed 's/.*v//'
}

nexus_panel_running_install_root() {
  local line
  line="$(pgrep -af 'threat-panel-http\.py' 2>/dev/null | head -1)" || return 1
  [[ -n "$line" ]] || return 1
  if [[ "$line" =~ threat-panel-http\.py[[:space:]]+[0-9]+[[:space:]]+([^[:space:]]+/panel) ]]; then
    dirname "${BASH_REMATCH[1]}"
    return 0
  fi
  awk '{
    for (i = 1; i <= NF; i++) {
      if ($i ~ /\/panel$/) { print $i; exit }
    }
  }' <<<"$line" | sed 's|/panel$||'
}

nexus_panel_stop() {
  local port="${NEXUS_THREAT_PANEL_PORT:-9477}"
  pkill -f "threat-panel-http.py.*${port}" 2>/dev/null || true
  if command -v fuser >/dev/null 2>&1; then
    fuser -k "${port}/tcp" 2>/dev/null || true
  fi
  nexus_await_port_free "${port}" 5
}

nexus_panel_pick_port() {
  local want="${1:-$(nexus_panel_desired_version 2>/dev/null || true)}"
  local primary="${NEXUS_THREAT_PANEL_PORT:-9477}"
  local fallback="${NEXUS_THREAT_PANEL_FALLBACK_PORT:-9478}"
  local served

  if ! curl -s --connect-timeout 1 "http://127.0.0.1:${primary}/field" >/dev/null 2>&1; then
    printf '%s' "$primary"
    return 0
  fi

  served="$(NEXUS_THREAT_PANEL_PORT="$primary" nexus_panel_served_version 2>/dev/null || true)"
  if [[ -z "$want" || -z "$served" || "$served" == "$want" ]]; then
    printf '%s' "$primary"
    return 0
  fi

  nexus_panel_stop
  served="$(NEXUS_THREAT_PANEL_PORT="$primary" nexus_panel_served_version 2>/dev/null || true)"
  if [[ -z "$served" || "$served" == "$want" ]]; then
    printf '%s' "$primary"
    return 0
  fi

  nexus_log "WARN" "panel-browser" "PORT_FALLBACK primary=${primary} served=${served} want=${want} -> ${fallback}"
  printf '%s' "$fallback"
}

nexus_panel_needs_restart() {
  local want="${1:-$(nexus_panel_desired_version)}"
  local port="${NEXUS_THREAT_PANEL_PORT:-9477}"
  local running_root served want_root

  [[ -n "$want" ]] || return 0
  want_root="${NEXUS_INSTALL_ROOT}"

  if ! pgrep -f "threat-panel-http.py.*${port}" >/dev/null 2>&1; then
    return 0
  fi

  running_root="$(nexus_panel_running_install_root 2>/dev/null || true)"
  if [[ -n "$running_root" && "$running_root" != "$want_root" ]]; then
    return 0
  fi

  served="$(nexus_panel_served_version 2>/dev/null || true)"
  if [[ -n "$served" && "$served" != "$want" ]]; then
    return 0
  fi

  return 1
}

nexus_panel_wait_ready() {
  local url="${1:-$(nexus_panel_url)}"
  local tries="${2:-5}"
  nexus_await_curl_ready "$url" "$tries" "$tries"
}

nexus_panel_boot_id() {
  local bid
  bid="$(cat /proc/sys/kernel/random/boot_id 2>/dev/null || true)"
  [[ -n "$bid" ]] || bid="boot-$(date -u '+%Y%m%d%H%M%S' 2>/dev/null || date '+%Y%m%d%H%M%S')"
  printf '%s' "$bid"
}

nexus_boot_c2_only_enabled() {
  [[ "${NEXUS_BOOT_C2_ONLY:-1}" == "1" ]]
}

nexus_boot_c2_prune_autostart() {
  local home="${HOME:-}"
  [[ -n "$home" ]] || return 0
  rm -f "${home}/.config/autostart/nexus-queen-world.desktop" 2>/dev/null || true
}

nexus_boot_c2_desktop() {
  local py="${NEXUS_PYTHONG:-pythong}"
  local open_py="${NEXUS_INSTALL_ROOT}/lib/field-queen-browser-open.py"
  [[ -f "$open_py" ]] || return 1
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-keyboard-sovereign.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/field-keyboard-sovereign.sh"
    nexus_keyboard_sovereign_engage
  fi
  nexus_boot_c2_prune_autostart
  NEXUS_AUTO_LAUNCH_QUEEN_BROWSER=0 \
  NEXUS_C2_DESKTOP_LAUNCH=0 \
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
  QUEEN_ROOT="${QUEEN_ROOT:-${NEXUS_INSTALL_ROOT}/Queen}" \
    "$py" "$open_py" desktop 2>/dev/null | grep -q '"ok": true'
}

nexus_panel_open_on_boot() {
  [[ "${NEXUS_PANEL_AUTO_OPEN:-1}" == "1" ]] || return 0
  local marker="${NEXUS_PANEL_LAUNCH_MARKER:-${NEXUS_STATE_DIR}/panel-launched.boot}"
  local boot_id
  boot_id="$(nexus_panel_boot_id)"
  if [[ -f "$marker" ]] && grep -qFx "$boot_id" "$marker" 2>/dev/null; then
    return 0
  fi
  if nexus_boot_c2_only_enabled; then
    if nexus_boot_c2_desktop; then
      printf '%s\n' "$boot_id" >"$marker"
      chmod 640 "$marker" 2>/dev/null || true
      nexus_log "INFO" "panel-browser" "BOOT_C2_DESKTOP ok"
      return 0
    fi
    nexus_log "WARN" "panel-browser" "BOOT_C2_DESKTOP_FAILED"
    return 1
  fi
  if nexus_panel_open_browser "${1:-$(nexus_panel_url)}"; then
    printf '%s\n' "$boot_id" >"$marker"
    chmod 640 "$marker" 2>/dev/null || true
    return 0
  fi
  return 1
}

nexus_panel_queen_open_py() {
  local route="${1:-}"
  local py="${NEXUS_INSTALL_ROOT}/lib/queen-panel-open.py"
  [[ -f "$py" ]] || return 1
  local pythong_bin="${NEXUS_PYTHONG:-pythong}"
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
  QUEEN_ROOT="${QUEEN_ROOT:-${NEXUS_INSTALL_ROOT}/Queen}" \
  NEXUS_THREAT_PANEL_PORT="${NEXUS_THREAT_PANEL_PORT:-9477}" \
  QUEEN_WORLD_PORT="${QUEEN_WORLD_PORT:-9481}" \
    "$pythong_bin" "$py" nexus "$route" 2>/dev/null
}

nexus_panel_open_queen_browser() {
  local url="${1:-$(nexus_panel_url)}"
  local route="" out ok=1
  if [[ "$url" == *"#"* ]]; then
    route="${url#*#}"
  fi
  out="$(nexus_panel_queen_open_py "$route")" && ok=0
  if [[ "$ok" -eq 0 ]] && grep -q '"ok": true' <<<"$out" 2>/dev/null; then
    nexus_log "INFO" "panel-browser" "QUEEN_TAB url=${url}"
    echo "Opened NEXUS in Queen browser tab: ${url}"
    return 0
  fi
  nexus_log "WARN" "panel-browser" "QUEEN_TAB_FAILED url=${url} out=${out:-empty}"
  return 1
}

nexus_panel_open_browser() {
  local url="${1:-$(nexus_panel_url)}"
  local ready_url
  ready_url="$(nexus_panel_app_url)"

  if ! nexus_panel_wait_ready "$ready_url" 5; then
    nexus_panel_wait_ready "$url" 5 || true
    nexus_panel_wait_ready "${url%/field}/" 5 || true
  fi
  if ! curl -fsS --connect-timeout 2 "$url" >/dev/null 2>&1 \
    && ! curl -fsS --connect-timeout 2 "$ready_url" >/dev/null 2>&1; then
    nexus_log "WARN" "panel-browser" "PANEL_NOT_READY url=${url}"
    return 1
  fi

  if nexus_panel_open_queen_browser "$url"; then
    return 0
  fi
  return 1
}

nexus_panel_open_help() {
  local url="${1:-$(nexus_panel_url)}"
  cat <<EOF
NEXUS C2 desktop URL: ${url}

Boot is C2-only — fullscreen AmmoOS command surface at /field.

  ./nexus.sh
  pythong ${NEXUS_INSTALL_ROOT}/lib/field-queen-browser-open.py open

Tray icon (right-click near clock):

  ./nexus.sh --tray

Or use the CLI (no browser needed):

  ./bin/nexus status
  ./bin/nexus test
EOF
}