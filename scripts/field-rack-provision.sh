#!/usr/bin/env bash
# One field per box — whole system to rack storage. Never colocate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-field-drive/nexus-field/state}"
PY="${PYTHON:-python3}"

log() { printf '[field-rack] %s\n' "$*"; }

# Unique box id — set FIELD_RACK_ID on physical racks; QEMU sets WORLD_PIPELINE_SLOT
: "${FIELD_RACK_ID:=rack-$(hostname -s 2>/dev/null || echo local)}"

log "assert solo field on box FIELD_RACK_ID=${FIELD_RACK_ID}"
"$PY" "$ROOT/lib/field-rack-uniqueness.py" assert | "$PY" -c "
import json,sys
d=json.load(sys.stdin)
if not d.get('ok'):
    print('BLOCKED colocation:', d.get('error'), d.get('collision'))
    sys.exit(1)
print('  field_id:', d.get('field_id'))
print('  rack_root:', d.get('rack_root'))
"

if [[ -n "${WORLD_PIPELINE_SLOT:-}" ]]; then
  log "QEMU slot ${WORLD_PIPELINE_SLOT} — provision GrokLab/deploy rack (no TEAM drive servers)"
  "$PY" "$ROOT/lib/field-zachub-qemu-racks.py" provision | "$PY" -c "
import json,sys
d=json.load(sys.stdin)
s=next((x for x in (d.get('slots') or []) if str(x.get('slot'))==str('${WORLD_PIPELINE_SLOT}')), {})
print('  field_id:', s.get('field_id'))
print('  storage:', s.get('storage_root'))
print('  role:', s.get('primary_role'))
"
  log "done — QEMU rack on GrokLab/deploy"
  exit 0
fi

log "publish whole nexus-field system to rack"
"$PY" "$ROOT/lib/field-rack-uniqueness.py" publish | "$PY" -c "
import json,sys
d=json.load(sys.stdin)
p=d.get('publish') or {}
print('  whole_system:', p.get('whole_system'))
print('  zachub_truth:', p.get('zachub_github_truth'))
print('  copied:', len(p.get('copied') or []), 'trees')
"

log "done — one field per box, never shared"