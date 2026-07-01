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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/aml-script-audit-master.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Master AML script audit — one script per iteration, fix-as-you-go until clean.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
AUDIT="$ROOT/lib/field-ammolang-script-audit.py"
PY=python3

log() { printf '[aml-script-audit-master] %s\n' "$*"; }

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'EOF'
Master script audit — sequential, no batching

  ./scripts/aml-script-audit-master.sh          # one script, stop on fail
  ./scripts/aml-script-audit-master.sh --loop   # repeat until all clean
  ./scripts/aml-script-audit-master.sh --drain  # one process, many scripts (still sequential)
  ./scripts/aml-script-audit-master.sh --reset  # clear audit state

On failure: read .nexus-state/ammolang-script-audit-repairs.json for agent repairs.
EOF
  exit 0
fi

if [[ "${1:-}" == "--reset" ]]; then
  exec "$PY" "$AUDIT" reset
fi

if [[ "${1:-}" == "--drain" ]]; then
  exec "$PY" "$AUDIT" run --drain
fi

if [[ "${1:-}" == "--loop" ]]; then
  log "loop mode — pass one script per iteration until complete"
  while true; do
    out="$("$PY" "$AUDIT" run)"
    printf '%s\n' "$out"
    ok="$(printf '%s' "$out" | "$PY" -c 'import json,sys; print(json.load(sys.stdin).get("ok"))')"
    complete="$(printf '%s' "$out" | "$PY" -c 'import json,sys; print(json.load(sys.stdin).get("complete"))')"
    if [[ "$ok" == "True" && "$complete" == "True" ]]; then
      log "all scripts clean"
      exit 0
    fi
    if [[ "$ok" != "True" ]]; then
      log "stopped — repair required"
      "$PY" "$AUDIT" report
      exit 1
    fi
  done
fi

log "single pass — one script checked"
exec "$PY" "$AUDIT" run