#!/usr/bin/env bash
# Planet GitHub sweep — stale trick, canonical indexes, true DNS/DHCP propagation.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
PY="${PYTHON:-python3}"

log() { printf '[sweep-github-planet] %s\n' "$*"; }

FAST=0
NO_RECORD=0
PROPAGATE=1
PUSH=0
REFIRE=0
for arg in "$@"; do
  case "$arg" in
    --fast) FAST=1 ;;
    --no-record) NO_RECORD=1 ;;
    --no-propagate) PROPAGATE=0 ;;
    --push) PUSH=1 ;;
    --refire|refire|RE-FIRE) REFIRE=1 ;;
  esac
done

ARGS=(sweep)
[[ "$REFIRE" -eq 1 ]] && ARGS=(refire)
[[ "$FAST" -eq 1 ]] && ARGS+=(--fast)
[[ "$NO_RECORD" -eq 1 ]] && ARGS+=(--no-record)

if [[ "$REFIRE" -eq 1 ]]; then
  log "RE-FIRE stale routes — enabled, never disable"
else
  log "sweep all GitHub repos → canonical DNS/DHCP index"
fi
"$PY" "$ROOT/lib/field-github-planet-sweep.py" "${ARGS[@]}" | "$PY" -c "
import json,sys
d=json.load(sys.stdin)
c=d.get('counts') or {}
print(f\"repos={c.get('repos_cataloged')} stale={c.get('stale_detected')} dns={c.get('dns_index_rows')} dhcp={c.get('dhcp_index_rows')}\")
"

if [[ "$PROPAGATE" -eq 1 ]]; then
  log "propagate endpoint registry → Hostess7/docs/api/"
  "$PY" "$ROOT/lib/field-github-planet-sweep.py" json > "$ROOT/Hostess7/docs/api/field-github-planet-sweep.json"
  bash "$ROOT/scripts/propagate-pages-registry.sh" sweep-github-planet.sh $([[ "$PUSH" -eq 1 ]] && echo --push)
fi

log "done — true DNS/DHCP indexes live at /api/field-github-planet-sweep"