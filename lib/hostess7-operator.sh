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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/hostess7-operator.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Hostess7 operator — autonomous NEXUS-Shield field sync (no preview-only update paths).

# shellcheck source=/dev/null
[[ -f "${NEXUS_INSTALL_ROOT:-}/lib/sg-paths.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/sg-paths.sh"
[[ -f "$(dirname "${BASH_SOURCE[0]}")/sg-paths.sh" ]] && source "$(dirname "${BASH_SOURCE[0]}")/sg-paths.sh"
sg_paths_export_defaults 2>/dev/null || true
HOSTESS7_ROOT="${HOSTESS7_ROOT:-$(sg_paths_hostess7_root 2>/dev/null)}"
# shellcheck source=/dev/null
[[ -f "${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}/lib/hostess7-field.sh" ]] \
  && source "${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}/lib/hostess7-field.sh"

nexus_hostess7_available() {
  [[ "${NEXUS_HOSTESS7_OPERATOR:-1}" == "1" ]] \
    && [[ -x "${HOSTESS7_ROOT}/Hostess7.sh" ]]
}

nexus_hostess7_sync_field() {
  nexus_hostess7_available || return 0
  [[ -x "${HOSTESS7_ROOT}/Hostess7.sh" ]] || return 0
  (
    cd "${HOSTESS7_ROOT}" || exit 0
    ./Hostess7.sh team-sync 2>/dev/null || true
  )
}

nexus_hostess7_nexus_update_apply() {
  [[ "${NEXUS_HOSTESS7_UPDATE_APPLY:-0}" == "1" ]] || return 0
  nexus_hostess7_available || return 0
  local src install_sh
  src="$(hostess7_nexus_source 2>/dev/null || true)"
  [[ -n "$src" ]] || return 0
  install_sh="${src}/stealth_install.sh"
  [[ -f "$install_sh" ]] || {
    nexus_log "WARN" "hostess7" "UPDATE_SKIP missing ${install_sh}"
    return 1
  }
  if [[ "$(id -u)" -eq 0 ]]; then
    bash "$install_sh"
    return $?
  fi
  if sudo -n true 2>/dev/null; then
    sudo -E bash "$install_sh"
    return $?
  fi
  nexus_log "INFO" "hostess7" "UPDATE_REQUIRES_SUDO — use panel UPDATE NOW or: sudo bash ${install_sh}"
  return 3
}

nexus_hostess7_autonomous_cycle() {
  [[ "${NEXUS_HOSTESS7_AUTONOMOUS:-1}" == "1" ]] || return 0
  nexus_hostess7_sync_field
  if declare -f nexus_hostess7_corroborate_integrity >/dev/null 2>&1; then
    nexus_hostess7_corroborate_integrity || true
  fi
}