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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/nexus-plugins.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS panel plugins — registry publish helpers.

nexus_plugins_json() {
  local script="${NEXUS_INSTALL_ROOT}/lib/nexus-plugins.py"
  if [[ ! -f "$script" ]]; then
    printf '{"schema":"nexus.plugins/v1","registry":[],"outputs":{}}'
    return 0
  fi
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
    pythong "$script" json 2>/dev/null \
    || printf '{"schema":"nexus.plugins/v1","registry":[],"outputs":{}}'
}

nexus_plugins_merge_panel() {
  local script="${NEXUS_INSTALL_ROOT}/lib/nexus-plugins.py"
  local panel="${NEXUS_THREAT_PANEL_JSON:-${NEXUS_STATE_DIR}/threat-panel.json}"
  [[ -f "$script" && -f "$panel" ]] || return 0
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
    pythong "$script" merge "$panel" >/dev/null 2>&1 || true
}