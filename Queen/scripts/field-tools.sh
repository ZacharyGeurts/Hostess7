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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:Queen/scripts/field-tools.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Queen Field Tools — Hostess 7 entry (status | probe | teach | run TOOL)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export QUEEN_ROOT="${QUEEN_ROOT:-$ROOT}"
export SG_ROOT="${SG_ROOT:-$(cd "${ROOT}/../.." && pwd)}"
export GROK16_ROOT="${GROK16_ROOT:-${SG_ROOT}/Grok16}"
export HOSTESS7_ROOT="${HOSTESS7_ROOT:-${SG_ROOT}/Hostess7}"
PY="${ROOT}/scripts/queen-py"
case "${1:-status}" in
  status|json) exec "${PY}" "${ROOT}/lib/queen-field-tools.py" json ;;
  probe) exec "${PY}" "${ROOT}/lib/queen-field-tools.py" probe ;;
  teach) exec "${PY}" "${ROOT}/lib/queen-field-tools.py" teach ;;
  run)
    shift
    exec "${PY}" "${ROOT}/lib/queen-field-tools.py" run "${1:-rtx}"
    ;;
  *)
    exec "${PY}" "${ROOT}/lib/queen-field-tools.py" dispatch <<<"$(printf '{"action":"%s"}' "${1:-status}")"
    ;;
esac