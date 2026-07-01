#!/usr/bin/env bash
# Quick deploy world field node on a fresh QEMU VM (port arg).
set -euo pipefail
export PATH="/usr/bin:/bin:/usr/sbin:/sbin"

PORT="${1:?usage: world-node-quick-deploy.sh SSH_PORT [NODE_ID] [REGION]}"
NODE_ID="${2:-node-qemu-unknown}"
REGION="${3:-unknown}"
SSH_KEY="${GROK_LAB_SSH_KEY:-$(cd "$(dirname "$0")" && pwd)/world-ssh/id_ed25519}"
NL="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
SG="${SG_ROOT:-$(cd "$NL/.." && pwd)}"
DEPLOY="$(cd "$(dirname "$0")" && pwd)"
BWLIMIT="${GROK_LAB_RSYNC_BWLIMIT:-${NEXUS_COOL_OPERATION:+8000}}"
BWLIMIT="${BWLIMIT:-0}"
RSYNC_BW=()
[[ -n "$BWLIMIT" && "$BWLIMIT" != "0" ]] && RSYNC_BW=(--bwlimit="$BWLIMIT")
RS="rsync -a ${RSYNC_BW[*]} -e 'ssh -p $PORT -i $SSH_KEY -o StrictHostKeyChecking=accept-new'"

log() { printf '[world-deploy] %s\n' "$*"; }

ssh -o ConnectTimeout=15 -p "$PORT" -i "$SSH_KEY" ubuntu@127.0.0.1 \
  'sudo /usr/bin/mkdir -p /opt/ammoos && sudo chown ubuntu:ubuntu /opt/ammoos && \
   /usr/bin/mkdir -p /opt/ammoos/ammoos/NewLatest/.nexus-state /opt/ammoos/ammoos/NewLatest/state \
   /opt/ammoos/ammoos/NewLatest/Grok16/{bin,lib,lib64,share,python,data,libexec/grok16} \
   /opt/ammoos/ammoos/NewLatest/KILROY/{boot,dist,rootfs,scripts,data,kernel,userspace,Grok}'

GROKLAB_EXCLUDES=(--exclude cache --exclude releases --exclude '*.log'
  --exclude deploy/qemu-vms --exclude deploy/dist --exclude deploy/stage
  --exclude deploy/bundles --exclude 'deploy/*.tar' --exclude 'deploy/*.tar.gz')
H7_EXCLUDES=(--exclude cache --exclude '*.pyc' --exclude __pycache__ --exclude brain/snapshots
  --exclude 'dist/hostess7-*-darwin-*' --exclude 'dist/hostess7-*-freebsd-*'
  --exclude 'dist/hostess7-*-aarch64*' --exclude 'dist/hostess7-*-windows-*')
if [[ -d "$NL/Hostess7" ]]; then
  log "rsync Hostess7 (slim) -> :$PORT"
  eval $RS "${H7_EXCLUDES[@]}" \
    "$NL/Hostess7/" "ubuntu@127.0.0.1:/opt/ammoos/ammoos/NewLatest/Hostess7/"
fi
if [[ -d "$NL/hostess7-training-viewer" ]]; then
  log "rsync hostess7-training-viewer -> :$PORT"
  eval $RS "$NL/hostess7-training-viewer/" \
    "ubuntu@127.0.0.1:/opt/ammoos/ammoos/NewLatest/hostess7-training-viewer/"
fi

for part in lib panel scripts data Queen Final_Eye ZNetwork; do
  log "rsync $part -> :$PORT"
  eval $RS --exclude cache --exclude releases --exclude '*.log' \
    "$NL/$part/" "ubuntu@127.0.0.1:/opt/ammoos/ammoos/NewLatest/$part/"
done
log "rsync GrokLab (slim) -> :$PORT"
eval $RS "${GROKLAB_EXCLUDES[@]}" \
  "$NL/GrokLab/" "ubuntu@127.0.0.1:/opt/ammoos/ammoos/NewLatest/GrokLab/"

# Grok16 + KILROY runtime
for part in python data lib lib64 share; do
  eval $RS "$NL/Grok16/$part/" "ubuntu@127.0.0.1:/opt/ammoos/ammoos/NewLatest/Grok16/$part/" 2>/dev/null || true
done
eval $RS "$NL/Grok16/libexec/grok16/" "ubuntu@127.0.0.1:/opt/ammoos/ammoos/NewLatest/Grok16/libexec/grok16/" 2>/dev/null || true
eval $RS --include='gpy-16' --include='g16-*' --exclude='*' "$NL/Grok16/bin/" "ubuntu@127.0.0.1:/opt/ammoos/ammoos/NewLatest/Grok16/bin/"
for part in boot dist rootfs scripts data kernel userspace Grok; do
  eval $RS "$NL/KILROY/$part/" "ubuntu@127.0.0.1:/opt/ammoos/ammoos/NewLatest/KILROY/$part/" 2>/dev/null || true
done

# Kill state + host security from home sanctuary
eval $RS "$NL/.nexus-state/field-hostile.tsv" "$NL/.nexus-state/kill-rekill-registry.json" \
  "$NL/.nexus-state/threat-panel.json" "$NL/state/" \
  "ubuntu@127.0.0.1:/opt/ammoos/ammoos/NewLatest/.nexus-state/" 2>/dev/null || true
/usr/bin/mkdir -p /tmp/wstate && /usr/bin/cp -a "$NL/.nexus-state/field-hostile.tsv" "$NL/.nexus-state/kill-rekill-registry.json" /tmp/wstate/ 2>/dev/null || true
eval $RS /tmp/wstate/ "ubuntu@127.0.0.1:/opt/ammoos/ammoos/NewLatest/.nexus-state/"
eval $RS "$NL/state/host-security-tier.json" "ubuntu@127.0.0.1:/opt/ammoos/ammoos/NewLatest/state/" 2>/dev/null || true

eval $RS --exclude qemu-vms --exclude dist --exclude stage --exclude bundles --exclude '*.tar' --exclude '*.tar.gz' \
  "$DEPLOY/" "ubuntu@127.0.0.1:/opt/ammoos/ammoos/NewLatest/GrokLab/deploy/"

log "bootstrap :$PORT $NODE_ID $REGION"
ssh -p "$PORT" -i "$SSH_KEY" ubuntu@127.0.0.1 "cd /opt/ammoos/ammoos/NewLatest && \
  export SG_ROOT=/opt/ammoos/ammoos NEXUS_INSTALL_ROOT=/opt/ammoos/ammoos/NewLatest \
  NEXUS_STATE_DIR=/opt/ammoos/ammoos/NewLatest/.nexus-state GROK_LAB_WORLD_NODE=1 \
  GROK_LAB_NODE_ID=$NODE_ID GROK_LAB_NODE_REGION=$REGION GROK_LAB_RELEASE_EYE=1 \
  ZOCR_VIRTUAL_EYE=1 && bash GrokLab/deploy/world-node-bootstrap.sh --installed --region $REGION --node-id $NODE_ID" 2>&1 | tail -15

log "done :$PORT"