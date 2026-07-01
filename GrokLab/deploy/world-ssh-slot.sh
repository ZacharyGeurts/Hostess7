#!/usr/bin/env bash
# SSH/rsync opts for loopback QEMU world slots (ports rotate across geographic nodes).
# Host keys change when a new VM binds the same port — never pin [127.0.0.1]:222x.
set -euo pipefail

WORLD_SSH_SLOT_OPTS=(
  -o BatchMode=yes
  -o ConnectTimeout=20
  -o StrictHostKeyChecking=no
  -o UserKnownHostsFile=/dev/null
  -o LogLevel=ERROR
)

world_ssh_clear_slot_key() {
  local port="${1:?port}"
  ssh-keygen -f "${HOME}/.ssh/known_hosts" -R "[127.0.0.1]:${port}" 2>/dev/null || true
}

world_ssh_rsync_e() {
  local port="${1:?port}" key="${2:?key}"
  printf "ssh -p %s -i %s -o BatchMode=yes -o ConnectTimeout=20 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" "$port" "$key"
}