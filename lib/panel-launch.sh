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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/panel-launch.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Panel launch — system desktop entry + taskbar tray (delegates to installer.sh).

# shellcheck source=/dev/null
[[ -f "${NEXUS_INSTALL_ROOT}/lib/panel-browser.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/panel-browser.sh"

nexus_panel_open_browser() {
  if declare -f nexus_boot_c2_desktop >/dev/null 2>&1 && nexus_boot_c2_only_enabled; then
    nexus_boot_c2_desktop
    return $?
  fi
  declare -f nexus_panel_open_on_boot >/dev/null 2>&1 \
    && nexus_panel_open_on_boot "${1:-$(nexus_panel_url 2>/dev/null || echo "http://127.0.0.1:${NEXUS_THREAT_PANEL_PORT:-9477}/field")}"
}

nexus_panel_install_desktop() {
  local root="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  [[ -f "${root}/lib/installer.sh" ]] || return 0
  # shellcheck source=/dev/null
  source "${root}/lib/installer.sh"
  local scope="system"
  [[ "$(id -u)" -eq 0 ]] || scope="user"
  nexus_install_linux_desktop "$root" "${SUDO_USER:-${INSTALL_USER:-$USER}}" "$scope"
  nexus_log "INFO" "panel-launch" "DESKTOP_ENTRY nexus-field (${scope})"
}