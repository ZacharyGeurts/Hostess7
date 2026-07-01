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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-depth-singularizer.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Field depth singularizer — daemon cycle hook (soft-touch defrag).
set -euo pipefail

nexus_depth_singularizer_cycle() {
  [[ "${NEXUS_SINGLE_FIELD_DEPTH:-1}" == "1" ]] || return 0
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-depth-singularizer.py" ]] || return 0
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    pythong "${NEXUS_INSTALL_ROOT}/lib/field-depth-singularizer.py" cycle >/dev/null 2>&1 || true
}