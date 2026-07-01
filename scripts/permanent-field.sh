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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/permanent-field.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Permanent fielding — SG + NewLatest from power input forward (no off switch).
set -euo pipefail

SG="$(cd "$(dirname "$0")/.." && pwd)"
NL="${NEXUS_INSTALL_ROOT:-$SG/NewLatest}"
STATE="${NEXUS_STATE_DIR:-$NL/.nexus-state}"
PY="$(command -v pythong || command -v python3)"

export SG_ROOT="$SG"
export NEXUS_INSTALL_ROOT="$NL"
export NEXUS_STATE_DIR="$STATE"

cmd="${1:-install}"
case "$cmd" in
  install|enable|commit)
    exec "$PY" "$NL/lib/field-permanent-fielding.py" install
    ;;
  status|json)
    exec "$PY" "$NL/lib/field-permanent-fielding.py" status
    ;;
  ensure|boot)
    exec "$PY" "$NL/lib/field-permanent-fielding.py" ensure
    ;;
  clear)
    exec "$PY" "$NL/lib/field-permanent-fielding.py" clear
    ;;
  *)
    echo "usage: $0 {install|status|ensure|clear}" >&2
    exit 1
    ;;
esac