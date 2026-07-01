#!/usr/bin/env bash
# Stop one QEMU world-node VM by id.
set -euo pipefail

ID="${1:?NODE_ID}"
DEPLOY="$(cd "$(dirname "$0")" && pwd)"
VM_DIR="${GROK_LAB_VM_DIR:-$DEPLOY/qemu-vms}"
pf="$VM_DIR/$ID/qemu.pid"
pid=""

if [[ -f "$pf" ]]; then
  pid="$(cat "$pf" 2>/dev/null || true)"
fi
if [[ -z "$pid" ]] || ! kill -0 "$pid" 2>/dev/null; then
  pid="$(pgrep -f "qemu-system-x86_64.*-name ${ID} " 2>/dev/null | head -1 || true)"
fi
if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
  kill "$pid" 2>/dev/null || true
  for _ in $(seq 1 20); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.25
  done
  kill -9 "$pid" 2>/dev/null || true
  echo "[qemu-stop-one] stopped $ID pid=$pid"
fi
rm -f "$pf"