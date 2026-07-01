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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-virus-guard.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Field Virus guard — gates file ingress/egress; HOSTILE until CIVILIAN or THREAT.
set -euo pipefail
_LIB="$(cd "$(dirname "$0")" && pwd)"
_ROOT="$(cd "${_LIB}/.." && pwd)"
# shellcheck source=/dev/null
source "${_LIB}/nexus-common.sh" 2>/dev/null || true
nexus_init_runtime_paths 2>/dev/null || true

export SG_ROOT="${SG_ROOT:-$(cd "${_ROOT}/.." && pwd)}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${_ROOT}/.nexus-state}"
export QUEEN_ROOT="${QUEEN_ROOT:-${SG_ROOT}/NewLatest/Queen}"
export SG_FIELD_VIRUS_INTERVAL="${SG_FIELD_VIRUS_INTERVAL:-12}"

PY="${QUEEN_ROOT}/lib/queen-field-virus.py"
if [[ ! -f "$PY" ]]; then
  exit 0
fi

# shellcheck source=/dev/null
[[ -f "${NEXUS_INSTALL_ROOT}/lib/ultra-stealth.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/ultra-stealth.sh"

exec pythong "$PY" guard