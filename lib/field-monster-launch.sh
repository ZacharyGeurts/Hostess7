#!/usr/bin/env bash
# Monster — universal secure launch wrapper. Every program should run through this.
# Usage: field-monster-launch.sh [--label NAME] [--stall SEC] [--timeout SEC] -- command [args...]
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${ROOT}/PythonG/bin/pythong"
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

ARGS=(run)
[[ -n "$LABEL" ]] && ARGS+=(--label "$LABEL")
[[ -n "$STALL" ]] && ARGS+=(--stall "$STALL")
[[ -n "$TIMEOUT" ]] && ARGS+=(--timeout "$TIMEOUT")
ARGS+=(-- "${CMD[@]}")

exec "$PY" "$MONSTER" "${ARGS[@]}"