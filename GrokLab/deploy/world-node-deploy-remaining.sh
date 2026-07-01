#!/usr/bin/env bash
# Deploy remaining QEMU world nodes one at a time — full stack + Hostess7 1.0.7h war verify.
set -euo pipefail

NL="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
DEPLOY="$(cd "$(dirname "$0")" && pwd)"

log() { printf '[world-batch] %s\n' "$*"; }

NODES=(
  "2224:node-qemu-ap-tokyo:ap-tokyo-1"
  "2225:node-qemu-ap-sydney:ap-sydney-1"
  "2226:node-qemu-sa-saopaulo:sa-saopaulo-1"
  "2227:node-qemu-ap-mumbai:ap-mumbai-1"
  "2228:node-qemu-uk-london:uk-london-1"
  "2229:node-qemu-ca-montreal:ca-montreal-1"
)

for spec in "${NODES[@]}"; do
  IFS=: read -r PORT NODE_ID REGION <<< "$spec"
  log "=== START $NODE_ID :$PORT ($REGION) ==="
  bash "$DEPLOY/world-node-quick-deploy.sh" "$PORT" "$NODE_ID" "$REGION"
  bash "$DEPLOY/world-node-hostess7-deploy.sh" "$PORT" "$NODE_ID" "$REGION"
  log "=== DONE $NODE_ID :$PORT ==="
done

log "all remaining nodes operational"