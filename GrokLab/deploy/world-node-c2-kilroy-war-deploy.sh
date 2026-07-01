#!/usr/bin/env bash
# Deploy NEXUS C2 + KILROY war hardening to one world node, then reboot.
set -euo pipefail
export PATH="/usr/bin:/bin:/usr/sbin:/sbin"

PORT="${1:?usage: world-node-c2-kilroy-war-deploy.sh SSH_PORT [NODE_ID] [REGION]}"
NODE_ID="${2:-node-qemu-unknown}"
REGION="${3:-unknown}"
REBOOT="${WORLD_NODE_REBOOT:-1}"

SSH_KEY="${GROK_LAB_SSH_KEY:-$(cd "$(dirname "$0")" && pwd)/world-ssh/id_ed25519}"
chmod 600 "$SSH_KEY" 2>/dev/null || true
SSH_OPTS="-o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20"
NL="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
SG="${SG_ROOT:-$(cd "$NL/.." && pwd)}"
KILROY="${KILROY_ROOT:-$(readlink -f "$NL/KILROY" 2>/dev/null || echo "$SG/KILROY")}"
DEPLOY="$(cd "$(dirname "$0")" && pwd)"
RB="/opt/ammoos/ammoos/NewLatest"
RS="rsync -a --delete-after -e 'ssh -p $PORT -i $SSH_KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20'"

log() { printf '[c2-kilroy-deploy] %s\n' "$*"; }

ssh_ok() {
  # shellcheck disable=SC2086
  ssh $SSH_OPTS -p "$PORT" -i "$SSH_KEY" ubuntu@127.0.0.1 "$@" 2>/dev/null
}

log "=== $NODE_ID :$PORT ($REGION) — NEXUS C2 + KILROY war harden ==="

for _ in $(seq 1 30); do
  ssh_ok "echo ready" | grep -q ready && break
  sleep 2
done
ssh_ok "echo ready" | grep -q ready || { log "SKIP — SSH not ready :$PORT"; exit 1; }

ssh_ok 'sudo /usr/bin/mkdir -p /opt/ammoos && sudo chown ubuntu:ubuntu /opt/ammoos && \
  /usr/bin/mkdir -p /opt/ammoos/ammoos/NewLatest/.nexus-state \
  /opt/ammoos/ammoos/NewLatest/KILROY/{boot,dist,rootfs,scripts,data,kernel,userspace,Grok} \
  /opt/ammoos/ammoos/NewLatest/GrokLab/deploy'

for part in lib panel scripts data config; do
  log "rsync $part -> :$PORT"
  eval $RS --exclude cache --exclude releases --exclude '*.log' --exclude __pycache__ \
    "$NL/$part/" "ubuntu@127.0.0.1:${RB}/$part/"
done

for f in nexus.sh nexus-launch.sh install.sh; do
  [[ -f "$NL/$f" ]] && eval $RS "$NL/$f" "ubuntu@127.0.0.1:${RB}/"
done

log "rsync KILROY -> :$PORT"
if [[ -d "$KILROY" ]]; then
  eval $RS "$KILROY/" "ubuntu@127.0.0.1:${RB}/KILROY/"
else
  log "WARN — KILROY missing at $KILROY"
fi

if [[ -d "$NL/Grok16/bin" ]]; then
  log "rsync Grok16 runtime (slim) -> :$PORT"
  ssh_ok "/usr/bin/mkdir -p ${RB}/Grok16/bin ${RB}/Grok16/python/driver"
  eval $RS --include='gpy-16' --include='g16-*' --exclude='*' "$NL/Grok16/bin/" "ubuntu@127.0.0.1:${RB}/Grok16/bin/" 2>/dev/null || true
  eval $RS "$NL/Grok16/python/driver/" "ubuntu@127.0.0.1:${RB}/Grok16/python/driver/" 2>/dev/null || true
fi

log "rsync GrokLab/deploy -> :$PORT"
eval $RS --exclude qemu-vms --exclude dist --exclude stage --exclude bundles \
  "$DEPLOY/" "ubuntu@127.0.0.1:${RB}/GrokLab/deploy/"

log "rsync kill state + war panel from sanctuary"
mkdir -p /tmp/wstate
for f in field-hostile.tsv kill-rekill-registry.json threat-panel.json settings.override field-war-hardening-panel.json; do
  [[ -f "$NL/.nexus-state/$f" ]] && cp -a "$NL/.nexus-state/$f" /tmp/wstate/ 2>/dev/null || true
done
eval $RS /tmp/wstate/ "ubuntu@127.0.0.1:${RB}/.nexus-state/" 2>/dev/null || true

ssh_ok "chmod +x ${RB}/GrokLab/deploy/world-node-c2-kilroy-boot.sh ${RB}/GrokLab/deploy/kilroy-war-arm.sh \
  ${RB}/GrokLab/deploy/nexus-c2-basement-arm.sh 2>/dev/null; \
  chmod +x ${RB}/lib/field-war-hardening.sh 2>/dev/null; true"

log "arm + boot C2/KILROY on :$PORT"
# shellcheck disable=SC2086
ssh $SSH_OPTS -p "$PORT" -i "$SSH_KEY" ubuntu@127.0.0.1 bash -s <<REMOTE || true
set -uo pipefail
export SG_ROOT=/opt/ammoos/ammoos
export NEXUS_INSTALL_ROOT=${RB}
export NEXUS_STATE_DIR=${RB}/.nexus-state
export GROK_LAB_NODE_ID=${NODE_ID}
export GROK_LAB_NODE_REGION=${REGION}
export GROK_LAB_WORLD_NODE=1
export AML_BUILD=0 NEXUS_WAR_MACHINE=1 NEXUS_EVERY_KILL_REKILL=1 NEXUS_BOOT_REKILL=1
AML_BUILD=0 bash ${RB}/GrokLab/deploy/world-node-c2-kilroy-boot.sh 2>&1 | tail -12 || true

# systemd — survive reboot
sudo tee /etc/systemd/system/nexus-c2-kilroy.service >/dev/null <<'UNIT'
[Unit]
Description=NEXUS C2 + KILROY war node
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
Environment=SG_ROOT=/opt/ammoos/ammoos
Environment=NEXUS_INSTALL_ROOT=/opt/ammoos/ammoos/NewLatest
Environment=NEXUS_STATE_DIR=/opt/ammoos/ammoos/NewLatest/.nexus-state
Environment=NEXUS_WAR_MACHINE=1
Environment=NEXUS_EVERY_KILL_REKILL=1
Environment=GROK_LAB_WORLD_NODE=1
ExecStart=/bin/bash /opt/ammoos/ammoos/NewLatest/GrokLab/deploy/world-node-c2-kilroy-boot.sh
TimeoutStartSec=180

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable nexus-c2-kilroy.service
REMOTE

if [[ "$REBOOT" == "1" ]]; then
  log "reboot :$PORT ($NODE_ID)"
  # shellcheck disable=SC2086
  ssh $SSH_OPTS -p "$PORT" -i "$SSH_KEY" ubuntu@127.0.0.1 'sudo /sbin/reboot' 2>/dev/null || true
  sleep 3
fi

log "done :$PORT $NODE_ID"