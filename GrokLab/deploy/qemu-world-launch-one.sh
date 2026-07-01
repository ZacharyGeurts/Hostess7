#!/usr/bin/env bash
# Launch one geographic node on a fixed QEMU slot port (does not stop other slots).
# Usage: qemu-world-launch-one.sh NODE_ID REGION SSH_PORT [MEM_MB]
set -euo pipefail

ID="${1:?NODE_ID}"
REGION="${2:?REGION}"
PORT="${3:?SSH_PORT}"
MEM="${4:-1024}"

DEPLOY="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=world-ssh-slot.sh
source "$DEPLOY/world-ssh-slot.sh"
world_ssh_clear_slot_key "$PORT"
VM_DIR="${GROK_LAB_VM_DIR:-$DEPLOY/qemu-vms}"
SSH_DIR="${GROK_LAB_SSH_DIR:-$DEPLOY/world-ssh}"
KEY="$SSH_DIR/id_ed25519"
IMG_URL="${GROK_LAB_CLOUD_IMG_URL:-https://cloud-images.ubuntu.com/minimal/releases/noble/release/ubuntu-24.04-minimal-cloudimg-amd64.img}"
BASE_IMG="$VM_DIR/ubuntu-24.04-minimal.img"

mkdir -p "$VM_DIR" "$SSH_DIR"
if [[ ! -f "$KEY" ]]; then
  ssh-keygen -t ed25519 -f "$KEY" -N "" -C "grok-lab-world" >/dev/null
  chmod 600 "$KEY"
fi
PUB="$(cat "${KEY}.pub")"

if [[ ! -f "$BASE_IMG" ]]; then
  echo "[qemu-one] downloading Ubuntu cloud image…"
  curl -fL --retry 3 -o "$BASE_IMG" "$IMG_URL"
fi

# Free this port if another node-qemu VM holds it
while read -r pid; do
  [[ -n "$pid" ]] || continue
  args="$(ps -p "$pid" -o args= 2>/dev/null || true)"
  [[ "$args" == *"hostfwd=tcp::${PORT}-:22"* ]] || continue
  old="$(echo "$args" | sed -n 's/.*-name \(node-qemu-[^ ]*\).*/\1/p')"
  if [[ -n "$old" && "$old" != "$ID" ]]; then
    bash "$DEPLOY/qemu-world-stop-one.sh" "$old" || true
  fi
done < <(pgrep -f 'qemu-system-x86_64.*node-qemu-' 2>/dev/null || true)

vm="$VM_DIR/$ID"
disk="$vm/disk.qcow2"
seed="$vm/seed.iso"
pidfile="$vm/qemu.pid"
mkdir -p "$vm/cloud-init"

if [[ ! -f "$disk" ]]; then
  qemu-img create -f qcow2 -b "$BASE_IMG" -F qcow2 "$disk" 12G >/dev/null
fi

cat >"$vm/cloud-init/meta-data" <<EOF
instance-id: ${ID}
local-hostname: ${ID}
EOF
cat >"$vm/cloud-init/user-data" <<EOF
#cloud-config
hostname: ${ID}
manage_etc_hosts: true
package_update: true
packages:
  - python3
  - python3-pip
  - curl
  - rsync
  - openssh-server
  - tesseract-ocr
  - qemu-guest-agent
ssh_authorized_keys:
  - ${PUB}
runcmd:
  - systemctl enable ssh
  - systemctl start ssh
EOF
genisoimage -quiet -output "$seed" -volid cidata -joliet -rock \
  "$vm/cloud-init/user-data" "$vm/cloud-init/meta-data"

if [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
  echo "[qemu-one] $ID already running pid=$(cat "$pidfile") port=$PORT"
  exit 0
fi
if pgrep -f "qemu-system-x86_64.*-name ${ID} " >/dev/null 2>&1; then
  echo "[qemu-one] $ID already running port=$PORT"
  exit 0
fi

nohup qemu-system-x86_64 \
  -name "$ID" \
  -m "$MEM" \
  -smp 2 \
  -cpu qemu64 \
  -drive "file=${disk},if=virtio,format=qcow2" \
  -drive "file=${seed},if=virtio,format=raw" \
  -netdev "user,id=net0,hostfwd=tcp::${PORT}-:22" \
  -device virtio-net-pci,netdev=net0 \
  -display none \
  -daemonize \
  -pidfile "$pidfile" \
  >>"$vm/qemu.log" 2>&1

echo "[qemu-one] launched $ID region=$REGION port=$PORT mem=${MEM}MB"