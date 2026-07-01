#!/usr/bin/env bash
# World node batches — 3 nodes per batch, 10 waves = 30 geographic nodes on 3 QEMU slots.
# Source: GrokLab/deploy/world-node-regions.json via world-nodes-sync.py
set -euo pipefail

DEPLOY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNC_PY="$DEPLOY/world-nodes-sync.py"

WORLD_BATCH_SIZE=3

world_batch_max() {
  python3 "$SYNC_PY" batch-max
}

world_batch_nodes() {
  local batch="${1:?usage: world_batch_nodes BATCH_NUM}"
  python3 "$SYNC_PY" batch-nodes "$batch"
}

world_batch_qemu_launch_specs() {
  local batch="${1:?}"
  python3 "$SYNC_PY" launch-specs "$batch"
}

world_node_port() {
  local id="${1:?}"
  python3 "$SYNC_PY" port-for-id "$id"
}