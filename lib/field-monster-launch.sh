#!/usr/bin/env bash
# Monster — universal secure launch wrapper. Every program should run through this.
# Usage: field-monster-launch.sh [--label NAME] [--stall SEC] [--timeout SEC] -- command [args...]
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${ROOT}/PythonG/bin/pythong"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3 2>/dev/null || echo python3)"
fi
MONSTER="${ROOT}/lib/field-monster-shell.py"
export PYTHONPATH="${ROOT}/lib:${PYTHONPATH:-}"

LABEL=""
STALL=""
TIMEOUT=""
CMD=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --label) LABEL="$2"; shift 2 ;;
    --stall) STALL="$2"; shift 2 ;;
    --timeout) TIMEOUT="$2"; shift 2 ;;
    --) shift; CMD=("$@"); break ;;
    *) CMD=("$@"); break ;;
  esac
done

if [[ ${#CMD[@]} -eq 0 ]]; then
  echo "monster: no command" >&2
  exit 2
fi

POLICY="${ROOT}/lib/field-monster-layer-policy.py"
AML="${ROOT}/lib/ammolang-run.sh"
if [[ -f "$POLICY" && -f "$AML" && "${MONSTER_SKIP_AML:-}" != "1" ]]; then
  NEEDS="$("$PY" "$POLICY" needs_ammolang --label "${LABEL:-launch}" -- "${CMD[@]}" 2>/dev/null || true)"
  if echo "$NEEDS" | grep -q '"needs_ammolang": true'; then
    TARGET="monster:${LABEL:-launch}"
    if [[ "${CMD[0]:-}" == *.py ]]; then
      TARGET="py:${CMD[0]#"$ROOT"/}"
      TARGET="${TARGET#./}"
    elif [[ "${CMD[0]:-}" == *scripts/* || "${CMD[0]:-}" == *.sh ]]; then
      TARGET="script:${CMD[0]#"$ROOT"/}"
      TARGET="${TARGET#./}"
    fi
    export MONSTER_LABEL="${LABEL:-launch}"
    export AML_BOUNDARY_ACTIVE=1
    exec bash "$AML" exec "$TARGET" -- "${CMD[@]}"
  fi
fi

ARGS=(run)
[[ -n "$LABEL" ]] && ARGS+=(--label "$LABEL")
[[ -n "$STALL" ]] && ARGS+=(--stall "$STALL")
[[ -n "$TIMEOUT" ]] && ARGS+=(--timeout "$TIMEOUT")
ARGS+=(-- "${CMD[@]}")

exec "$PY" "$MONSTER" "${ARGS[@]}"