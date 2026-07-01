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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/root-sovereign-guard.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Invisible root sovereignty guard — unauthorized root killed with prejudice.
set -euo pipefail
_LIB="$(cd "$(dirname "$0")" && pwd)"
_ROOT="$(cd "${_LIB}/.." && pwd)"
# shellcheck source=/dev/null
source "${_LIB}/nexus-common.sh" 2>/dev/null || true
nexus_init_runtime_paths 2>/dev/null || true

export SG_ROOT="${SG_ROOT:-$(cd "${_ROOT}/.." && pwd)}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${_ROOT}/.nexus-state}"
export QUEEN_ROOT="${QUEEN_ROOT:-${SG_ROOT}/NewLatest/Queen}"
export SG_ROOT_SOVEREIGN_AUTO_BIND="${SG_ROOT_SOVEREIGN_AUTO_BIND:-1}"
export SG_ROOT_GUARD_INTERVAL="${SG_ROOT_GUARD_INTERVAL:-8}"
export SG_ROOT_GUARD_FAST_INTERVAL="${SG_ROOT_GUARD_FAST_INTERVAL:-4}"
export SG_ROOT_SOVEREIGN_KILL="${SG_ROOT_SOVEREIGN_KILL:-1}"
export SG_ROOT_KILL_PREJUDICE="${SG_ROOT_KILL_PREJUDICE:-1}"

PY="${QUEEN_ROOT}/lib/queen-root-sovereign.py"
if [[ ! -f "$PY" ]]; then
  exit 0
fi

# Ultra-stealth pacing — stays under CPU budget
# shellcheck source=/dev/null
[[ -f "${NEXUS_INSTALL_ROOT}/lib/ultra-stealth.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/ultra-stealth.sh"

exec pythong "$PY" guard