#!/usr/bin/env bash
# Deploy NEXUS C2 + KILROY war hardening to all core world nodes (5 VM cap), then reboot each.
set -euo pipefail

DEPLOY="$(cd "$(dirname "$0")" && pwd)"
NL="${NEXUS_INSTALL_ROOT:-$(cd "$DEPLOY/../../.." && pwd)}"
LOG="${NEXUS_STATE_DIR:-$NL/.nexus-state}/world-c2-kilroy-deploy.log"
mkdir -p "$(dirname "$LOG")"

log() { printf '[c2-kilroy-all] %s\n' "$*" | tee -a "$LOG"; }

# Core 5 nodes (qemu cap)
NODES=(
  "2222:node-qemu-us-phoenix:us-phoenix-1"
  "2223:node-qemu-eu-frankfurt:eu-frankfurt-1"
  "2224:node-qemu-ap-tokyo:ap-tokyo-1"
  "2225:node-qemu-ap-sydney:ap-sydney-1"
  "2226:node-qemu-sa-saopaulo:sa-saopaulo-1"
)

log "=== world C2+KILROY war deploy begin $(date -u '+%Y-%m-%dT%H:%M:%SZ') ==="

for spec in "${NODES[@]}"; do
  IFS=: read -r PORT NODE_ID REGION <<< "$spec"
  if bash "$DEPLOY/world-node-c2-kilroy-war-deploy.sh" "$PORT" "$NODE_ID" "$REGION" >>"$LOG" 2>&1; then
    log "OK $NODE_ID :$PORT"
  else
    log "FAIL $NODE_ID :$PORT"
  fi
done

log "waiting for post-reboot SSH (up to 180s per node)…"
KEY="${GROK_LAB_SSH_KEY:-$DEPLOY/world-ssh/id_ed25519}"
for spec in "${NODES[@]}"; do
  IFS=: read -r PORT NODE_ID REGION <<< "$spec"
  ok=0
  for _ in $(seq 1 60); do
    if ssh -o BatchMode=yes -o ConnectTimeout=4 -o StrictHostKeyChecking=accept-new \
        -p "$PORT" -i "$KEY" ubuntu@127.0.0.1 "curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1:9477/field 2>/dev/null || echo 000" 2>/dev/null | grep -q 200; then
      log "VERIFY OK $NODE_ID :$PORT panel=200"
      ok=1
      break
    fi
    sleep 3
  done
  [[ "$ok" -eq 1 ]] || log "VERIFY WARN $NODE_ID :$PORT panel not 200 yet"
done

log "=== world C2+KILROY war deploy complete ==="