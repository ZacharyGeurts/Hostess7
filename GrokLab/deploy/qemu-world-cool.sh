#!/usr/bin/env bash
# Suspend/resume QEMU world VMs to save host CPU/RAM.
set -euo pipefail

DEPLOY="$(cd "$(dirname "$0")" && pwd)"
VM_DIR="${GROK_LAB_VM_DIR:-$DEPLOY/qemu-vms}"
MODE="${1:-status}"
KEEP_PORTS="${GROK_LAB_COOL_KEEP_PORTS:-2222,2223}"

log() { printf '[qemu-cool] %s\n' "$*"; }

_vm_pid() {
  local id="$1"
  local pf="$VM_DIR/$id/qemu.pid"
  local pid=""
  if [[ -f "$pf" ]]; then
    pid="$(cat "$pf" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      printf '%s' "$pid"
      return 0
    fi
  fi
  # pidfile may be gone while VM still runs (deleted qemu-vms dir, stale file)
  pid="$(pgrep -f "qemu-system-x86_64.*-name ${id} " 2>/dev/null | head -1 || true)"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    printf '%s' "$pid"
    return 0
  fi
  return 1
}

_port_for_id() {
  case "$1" in
    node-qemu-us-phoenix) echo 2222 ;;
    node-qemu-eu-frankfurt) echo 2223 ;;
    node-qemu-ap-tokyo) echo 2224 ;;
    node-qemu-ap-sydney) echo 2225 ;;
    node-qemu-sa-saopaulo) echo 2226 ;;
    node-qemu-ap-mumbai) echo 2227 ;;
    node-qemu-uk-london) echo 2228 ;;
    node-qemu-ca-montreal) echo 2229 ;;
    *) echo 0 ;;
  esac
}

_keep_port() {
  local port="$1"
  [[ ",${KEEP_PORTS}," == *",${port},"* ]]
}

_vm_ids() {
  local id
  if [[ -d "$VM_DIR" ]]; then
    for id in "$VM_DIR"/node-qemu-*/; do
      [[ -d "$id" ]] || continue
      basename "$id"
    done
    return 0
  fi
  # VM metadata dir may be gone while qemu processes still run
  pgrep -af 'qemu-system-x86_64.*-name node-qemu-' 2>/dev/null \
    | sed -n 's/.*-name \(node-qemu-[^ ]*\).*/\1/p' \
    | sort -u
}

_suspend_vm() {
  local id="$1" pid
  pid="$(_vm_pid "$id")" || return 0
  if kill -STOP "$pid" 2>/dev/null; then
    log "suspended $id pid=$pid"
  fi
}

_resume_vm() {
  local id="$1" pid
  pid="$(_vm_pid "$id")" || return 0
  if kill -CONT "$pid" 2>/dev/null; then
    log "resumed $id pid=$pid"
  fi
}

case "$MODE" in
  suspend-idle)
    while IFS= read -r id; do
      [[ -n "$id" ]] || continue
      port="$(_port_for_id "$id")"
      if _keep_port "$port"; then
        log "keep warm $id :$port"
        continue
      fi
      _suspend_vm "$id"
    done < <(_vm_ids)
    ;;
  resume-all)
    while IFS= read -r id; do
      [[ -n "$id" ]] || continue
      _resume_vm "$id"
    done < <(_vm_ids)
    ;;
  status)
    while IFS= read -r id; do
      [[ -n "$id" ]] || continue
      pid="$(_vm_pid "$id" 2>/dev/null || true)"
      [[ -n "$pid" ]] || continue
      st="$(ps -o stat= -p "$pid" 2>/dev/null | tr -d ' ' || echo ?)"
      log "$id pid=$pid stat=$st port=$(_port_for_id "$id")"
    done < <(_vm_ids)
    ;;
  *)
    echo "usage: $0 [suspend-idle|resume-all|status]" >&2
    exit 1
    ;;
esac