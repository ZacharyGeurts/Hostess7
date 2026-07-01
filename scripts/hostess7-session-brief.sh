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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/hostess7-session-brief.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Brief Hostess 7 — operator Brief/Evaluate/Task + virtual workspace mandate.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-state}"
export HOSTESS7_ROOT="${HOSTESS7_ROOT:-${ROOT}/Hostess7}"
export PATH="${ROOT}/PythonG/bin:${PATH:-}"

PY="${NEXUS_PYTHONG:-pythong}"
command -v "$PY" >/dev/null 2>&1 || PY=python3

BRIEF='Hostess 7 mandate: Brief, Evaluate, Task. Edit yourself ONLY in virtual workspace — test CHIPS G16 Python die, debug, then promote with PROMOTE. Field tasks via ammolang-run.sh. AmmoOS: simple, informative, secure, protecting, no hostility.'

"$PY" "${ROOT}/lib/hostess7-operator.py" brief "$BRIEF" || true
"$PY" "${ROOT}/Hostess7/scripts/field_superintelligence.py" inbox "$BRIEF" || true
"$PY" "${ROOT}/lib/hostess7-virtual-workspace.py" ensure
"$PY" "${ROOT}/lib/hostess7-virtual-workspace.py" teach "virtual workspace chips debug"
"$PY" "${ROOT}/lib/hostess7-operator.py" catalog
"$PY" "${ROOT}/lib/hostess7-tasklist.py" seed
"$PY" "${ROOT}/lib/hostess7-tasklist.py" report