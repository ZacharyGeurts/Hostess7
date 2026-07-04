#!/usr/bin/env bash
# AmmoDrive fork guard — burn stale clones, true source only.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
export SG_ROOT="${SG_ROOT:-$(dirname "$ROOT")}"
PY="${PYTHON:-python3}"

log() { printf '[zachub-fork-guard] %s\n' "$*"; }

DRY=0
NO_GH=0
NO_RECORD=0
PROPAGATE=1
CMD="guard"
for arg in "$@"; do
  case "$arg" in
    --dry|dry) DRY=1; CMD="dry" ;;
    --no-gh) NO_GH=1 ;;
    --no-record) NO_RECORD=1 ;;
    --no-propagate) PROPAGATE=0 ;;
    status|scan|json|burn|run) CMD="$arg" ;;
  esac
done

ARGS=("$CMD")
[[ "$DRY" -eq 1 ]] && ARGS+=(--dry)
[[ "$NO_GH" -eq 1 ]] && ARGS+=(--no-gh)
[[ "$NO_RECORD" -eq 1 ]] && ARGS+=(--no-record)

log "ALL RIGHTS RESERVED — AmmoDrive fork guard for ${GITHUB_ACCOUNT:-ZacharyGeurts}"
"$PY" "$ROOT/lib/field-zachub-fork-guard.py" "${ARGS[@]}" | "$PY" -c "
import json,sys
d=json.load(sys.stdin)
c=d.get('counts') or {}
print(f\"local={c.get('local_findings')} forks_del={c.get('fork_deletes')} locks={c.get('fork_locks')} branches={c.get('branch_cuts')} gh={d.get('gh_available')}\")
"

if [[ "$PROPAGATE" -eq 1 && "$CMD" != "scan" && "$CMD" != "status" ]]; then
  API_DIR="$ROOT/Hostess7/docs/api"
  mkdir -p "$API_DIR"
  log "propagate panel snapshot → Hostess7/docs/api/field-zachub-fork-guard.json"
  PROP_ARGS=(json)
  [[ "$NO_GH" -eq 1 ]] && PROP_ARGS+=(--no-gh)
  [[ "$NO_RECORD" -eq 1 ]] && PROP_ARGS+=(--no-record)
  "$PY" "$ROOT/lib/field-zachub-fork-guard.py" "${PROP_ARGS[@]}" > "$API_DIR/field-zachub-fork-guard.json"
fi

log "done — /api/field-zachub-fork-guard"