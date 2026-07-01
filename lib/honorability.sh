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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/honorability.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Honorability + browser awareness + operator location — panel publish helpers.

nexus_honorability_json() {
  local script="${NEXUS_INSTALL_ROOT}/lib/browser-awareness.py"
  if [[ ! -f "$script" ]]; then
    printf '{"active_sites":[],"honorability":{"entries":[]}}'
    return 0
  fi
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
    pythong "$script" json 2>/dev/null || printf '{"active_sites":[],"honorability":{"entries":[]}}'
}

nexus_operator_location_json() {
  local script="${NEXUS_INSTALL_ROOT}/lib/operator-location.py"
  if [[ ! -f "$script" ]]; then
    printf '{"lat":null,"lon":null,"source":"unset"}'
    return 0
  fi
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
    pythong "$script" json 2>/dev/null || printf '{"lat":null,"lon":null,"source":"unset"}'
}