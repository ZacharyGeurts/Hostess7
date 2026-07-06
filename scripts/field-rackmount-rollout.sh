#!/usr/bin/env bash
# Staged Grok rackmount rollout — one stage at a time, checkpointed ledger.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
export HOSTESS7_SUDO_PW="${HOSTESS7_SUDO_PW:-mememe}"
export SUDO_PW="$HOSTESS7_SUDO_PW"
PY="${PYTHON:-python3}"

STAGE="${1:-}"
THROUGH="${2:-}"

log() { printf '[rackmount-rollout] %s\n' "$*"; }

usage() {
  cat <<'EOF'
Staged rackmount rollout (sudo mememe for killers stage)

  bash scripts/field-rackmount-rollout.sh              # next pending stage
  bash scripts/field-rackmount-rollout.sh 0            # stage 0 cleanup
  bash scripts/field-rackmount-rollout.sh 2 4          # stages 2→4 inclusive
  bash scripts/field-rackmount-rollout.sh staged 6     # alias: run through stage 6
  bash scripts/field-rackmount-rollout.sh status       # show ledger + inventory

Stages:
  0 cleanup     — stop failed units, kill rogue PIDs, kgo once
  1 inventory   — baseline rack inventory
  2 provision   — QEMU rack slots on GrokLab/deploy
  3 dns_dhcp    — DNS/DHCP primary fix + keepalive
  4 collisions  — collision guard enforce, shard check
  5 killers     — spawner-kill + kgo always-on (sudo)
  6 sync        — refresh inventory, verify APIs
  7 probe       — probe racks for screen pickup
EOF
}

if [[ "${STAGE:-}" == "status" || "${STAGE:-}" == "help" || "${STAGE:-}" == "-h" ]]; then
  usage
  "$PY" "$ROOT/lib/field-rack-inventory.py" json --fast 2>/dev/null | "$PY" -c "
import json,sys
d=json.load(sys.stdin)
c=d.get('counts') or {}
print('inventory:', c.get('up'), '/', c.get('total'), 'up,', c.get('available'), 'available')
" || true
  if [[ -f "$NEXUS_STATE_DIR/field-rack-rollout-ledger.json" ]]; then
    "$PY" -c "
import json
d=json.load(open('$NEXUS_STATE_DIR/field-rack-rollout-ledger.json'))
for s in (d.get('stages') or [])[-8:]:
    print(' ', s.get('stage_id') or s.get('stage'), s.get('title') or s.get('stage_name'), 'ok='+str(s.get('ok')))
last=d.get('last') or {}
if last.get('next_stage'):
    print('next:', last['next_stage'].get('id'), last['next_stage'].get('name'))
"
  fi
  exit 0
fi

# world-nodes seed (avoid Hostess7 tree)
EXAMPLE="$ROOT/GrokLab/deploy/world-nodes.example.json"
NODES="$ROOT/GrokLab/deploy/world-nodes.json"
if [[ ! -f "$EXAMPLE" ]]; then
  log "seed world-nodes.example.json (sudo if deploy root-owned)"
  SEED="$(mktemp)"
  cat >"$SEED" <<'JSON'
{
  "schema": "grok-lab-world-nodes/v1",
  "motto": "A new internet everywhere, from each and every home",
  "nodes": [
    {
      "id": "node-local",
      "enabled": true,
      "region": "local",
      "provider": "sovereign-host",
      "role": "home_sanctuary"
    }
  ]
}
JSON
  if cp "$SEED" "$EXAMPLE" 2>/dev/null; then
    :
  else
    echo "$HOSTESS7_SUDO_PW" | sudo -S cp "$SEED" "$EXAMPLE" 2>/dev/null || true
    echo "$HOSTESS7_SUDO_PW" | sudo -S chown "$(id -un):$(id -gn)" "$EXAMPLE" 2>/dev/null || true
  fi
  rm -f "$SEED"
fi
if [[ ! -f "$NODES" && -f "$EXAMPLE" ]]; then
  cp "$EXAMPLE" "$NODES" 2>/dev/null || echo "$HOSTESS7_SUDO_PW" | sudo -S cp "$EXAMPLE" "$NODES" 2>/dev/null || true
  log "copied world-nodes.json from example"
fi

ARGS=(staged)
if [[ -n "$STAGE" ]]; then
  ARGS+=( "$STAGE" )
  if [[ -n "$THROUGH" ]]; then
    ARGS+=( "$THROUGH" )
  fi
fi

log "running: field-rack-inventory.py ${ARGS[*]}"
OUT="$("$PY" "$ROOT/lib/field-rack-inventory.py" "${ARGS[@]}")"
echo "$OUT" | "$PY" -c "
import json,sys
d=json.load(sys.stdin)
for r in d.get('ran') or []:
    sid=r.get('stage_id') or r.get('stage')
    print(f\"  stage {sid} {r.get('title') or r.get('stage_name')}: ok={r.get('ok')}\")
print('overall ok:', d.get('ok'))
n=d.get('next_stage')
if n:
    print('next stage:', n.get('id'), n.get('name'), '-', n.get('title'))
"

if echo "$OUT" | "$PY" -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('ok') else 1)"; then
  log "staged rollout checkpoint OK"
else
  log "WARN: stage reported failure — check .nexus-state/field-rack-rollout-ledger.json"
  exit 1
fi