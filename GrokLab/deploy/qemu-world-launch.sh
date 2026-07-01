#!/usr/bin/env bash
# Launch QEMU Ubuntu world field nodes (free VM stand-ins when no cloud API).
set -euo pipefail

DEPLOY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB="$(cd "$DEPLOY/.." && pwd)"
VM_DIR="${GROK_LAB_VM_DIR:-$DEPLOY/qemu-vms}"
SSH_DIR="${GROK_LAB_SSH_DIR:-$DEPLOY/world-ssh}"
KEY="$SSH_DIR/id_ed25519"
IMG_URL="${GROK_LAB_CLOUD_IMG_URL:-https://cloud-images.ubuntu.com/minimal/releases/noble/release/ubuntu-24.04-minimal-cloudimg-amd64.img}"
BASE_IMG="$VM_DIR/ubuntu-24.04-minimal.img"
PY="${GROK_LAB_PY:-python3}"

mkdir -p "$VM_DIR" "$SSH_DIR"

if [[ ! -f "$KEY" ]]; then
  ssh-keygen -t ed25519 -f "$KEY" -N "" -C "grok-lab-world" >/dev/null
  chmod 600 "$KEY"
fi
PUB="$(cat "${KEY}.pub")"

if [[ ! -f "$BASE_IMG" ]]; then
  echo "[qemu-world] downloading Ubuntu cloud image…"
  curl -fL --retry 3 -o "$BASE_IMG" "$IMG_URL"
fi

launch_vm() {
  local id="$1" region="$2" port="$3" mem="${4:-2048}"
  local vm="$VM_DIR/$id"
  local disk="$vm/disk.qcow2"
  local seed="$vm/seed.iso"
  local pidfile="$vm/qemu.pid"
  mkdir -p "$vm/cloud-init"

  if [[ ! -f "$disk" ]]; then
    qemu-img create -f qcow2 -b "$BASE_IMG" -F qcow2 "$disk" 12G >/dev/null
  fi

  cat >"$vm/cloud-init/meta-data" <<EOF
instance-id: ${id}
local-hostname: ${id}
EOF
  cat >"$vm/cloud-init/user-data" <<EOF
#cloud-config
hostname: ${id}
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
    echo "[qemu-world] $id already running pid=$(cat "$pidfile") port=$port"
    return 0
  fi

  nohup qemu-system-x86_64 \
    -name "$id" \
    -m "$mem" \
    -smp 2 \
    -cpu qemu64 \
    -drive "file=${disk},if=virtio,format=qcow2" \
    -drive "file=${seed},if=virtio,format=raw" \
    -netdev "user,id=net0,hostfwd=tcp::${port}-:22" \
    -device virtio-net-pci,netdev=net0 \
    -display none \
    -daemonize \
    -pidfile "$pidfile" \
    >>"$vm/qemu.log" 2>&1

  echo "[qemu-world] launched $id region=$region ssh_port=$port"
}

# Simulated world regions on loopback SSH forwards (free VM stand-ins)
launch_vm "node-qemu-us-phoenix" "us-phoenix-1" 2222 1536
launch_vm "node-qemu-eu-frankfurt" "eu-frankfurt-1" 2223 1536
launch_vm "node-qemu-ap-tokyo" "ap-tokyo-1" 2224 1536
launch_vm "node-qemu-ap-sydney" "ap-sydney-1" 2225 1536
launch_vm "node-qemu-sa-saopaulo" "sa-saopaulo-1" 2226 1536
launch_vm "node-qemu-ap-mumbai" "ap-mumbai-1" 2227 1024
launch_vm "node-qemu-uk-london" "uk-london-1" 2228 1024
launch_vm "node-qemu-ca-montreal" "ca-montreal-1" 2229 1024

# Update world-nodes.json with live QEMU targets
DEPLOY="$DEPLOY" KEY="$KEY" "$PY" - <<'PY'
import json, os
from pathlib import Path
deploy = Path(os.environ["DEPLOY"])
key = os.environ["KEY"]
nodes_path = deploy / "world-nodes.json"
doc = json.loads(nodes_path.read_text(encoding="utf-8"))
qemu_nodes = [
    {"id": "node-qemu-us-phoenix", "region": "us-phoenix-1", "provider": "qemu-free",
     "role": "field_node", "ssh": "ubuntu@127.0.0.1", "ssh_port": 2222,
     "ssh_key": key, "enabled": True,
     "tunnel": f"ssh -N -L 19477:127.0.0.1:9477 -p 2222 -i {key} ubuntu@127.0.0.1"},
    {"id": "node-qemu-eu-frankfurt", "region": "eu-frankfurt-1", "provider": "qemu-free",
     "role": "field_node", "ssh": "ubuntu@127.0.0.1", "ssh_port": 2223,
     "ssh_key": key, "enabled": True,
     "tunnel": f"ssh -N -L 19478:127.0.0.1:9477 -p 2223 -i {key} ubuntu@127.0.0.1"},
    {"id": "node-qemu-ap-tokyo", "region": "ap-tokyo-1", "provider": "qemu-free",
     "role": "field_node", "ssh": "ubuntu@127.0.0.1", "ssh_port": 2224,
     "ssh_key": key, "enabled": True,
     "tunnel": f"ssh -N -L 19479:127.0.0.1:9477 -p 2224 -i {key} ubuntu@127.0.0.1"},
    {"id": "node-qemu-ap-sydney", "region": "ap-sydney-1", "provider": "qemu-free",
     "role": "field_node", "ssh": "ubuntu@127.0.0.1", "ssh_port": 2225,
     "ssh_key": key, "enabled": True,
     "tunnel": f"ssh -N -L 19480:127.0.0.1:9477 -p 2225 -i {key} ubuntu@127.0.0.1"},
    {"id": "node-qemu-sa-saopaulo", "region": "sa-saopaulo-1", "provider": "qemu-free",
     "role": "field_node", "ssh": "ubuntu@127.0.0.1", "ssh_port": 2226,
     "ssh_key": key, "enabled": True,
     "tunnel": f"ssh -N -L 19481:127.0.0.1:9477 -p 2226 -i {key} ubuntu@127.0.0.1"},
    {"id": "node-qemu-ap-mumbai", "region": "ap-mumbai-1", "provider": "qemu-free",
     "role": "field_node", "ssh": "ubuntu@127.0.0.1", "ssh_port": 2227,
     "ssh_key": key, "enabled": True,
     "tunnel": f"ssh -N -L 19482:127.0.0.1:9477 -p 2227 -i {key} ubuntu@127.0.0.1"},
    {"id": "node-qemu-uk-london", "region": "uk-london-1", "provider": "qemu-free",
     "role": "field_node", "ssh": "ubuntu@127.0.0.1", "ssh_port": 2228,
     "ssh_key": key, "enabled": True,
     "tunnel": f"ssh -N -L 19483:127.0.0.1:9477 -p 2228 -i {key} ubuntu@127.0.0.1"},
    {"id": "node-qemu-ca-montreal", "region": "ca-montreal-1", "provider": "qemu-free",
     "role": "field_node", "ssh": "ubuntu@127.0.0.1", "ssh_port": 2229,
     "ssh_key": key, "enabled": True,
     "tunnel": f"ssh -N -L 19484:127.0.0.1:9477 -p 2229 -i {key} ubuntu@127.0.0.1"},
]
keep = [n for n in doc.get("nodes", []) if n.get("id") == "node-local"]
doc["nodes"] = keep + qemu_nodes
doc["qemu"] = {"launched": True, "ssh_key": key}
nodes_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"ok": True, "nodes": len(doc["nodes"]), "path": str(nodes_path)}, indent=2))
PY

echo "[qemu-world] waiting for SSH (up to 120s)…"
for spec in "2222:node-qemu-us-phoenix" "2223:node-qemu-eu-frankfurt" "2224:node-qemu-ap-tokyo" "2225:node-qemu-ap-sydney" "2226:node-qemu-sa-saopaulo" "2227:node-qemu-ap-mumbai" "2228:node-qemu-uk-london" "2229:node-qemu-ca-montreal"; do
  port="${spec%%:*}"
  name="${spec##*:}"
  ok=0
  for _ in $(seq 1 60); do
    if ssh -o BatchMode=yes -o ConnectTimeout=2 -o StrictHostKeyChecking=accept-new \
        -p "$port" -i "$KEY" "ubuntu@127.0.0.1" "echo ready" 2>/dev/null | grep -q ready; then
      echo "[qemu-world] $name SSH ready on :$port"
      ok=1
      break
    fi
    sleep 2
  done
  [[ "$ok" -eq 1 ]] || echo "[qemu-world] WARN: $name not ready on :$port" >&2
done