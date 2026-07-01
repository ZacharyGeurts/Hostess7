#!/usr/bin/env bash
# Push Hostess7 1.0.7h (war-ready) to one QEMU world node — verify before next VM.
set -euo pipefail

PORT="${1:?usage: world-node-hostess7-deploy.sh SSH_PORT [NODE_ID] [REGION]}"
NODE_ID="${2:-node-qemu-unknown}"
REGION="${3:-unknown}"
SSH_KEY="${GROK_LAB_SSH_KEY:-$(cd "$(dirname "$0")" && pwd)/world-ssh/id_ed25519}"
NL="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
SG="${SG_ROOT:-$(cd "$NL/.." && pwd)}"
H7="${HOSTESS7_ROOT:-$NL/Hostess7}"
H7_EXCLUDES=(
  --exclude cache
  --exclude '*.pyc'
  --exclude __pycache__
  --exclude .git
  --exclude brain/snapshots
  --exclude 'dist/hostess7-*-darwin-*'
  --exclude 'dist/hostess7-*-freebsd-*'
  --exclude 'dist/hostess7-*-aarch64*'
  --exclude 'dist/hostess7-*-windows-*'
)
TV_EXCLUDES=(--exclude __pycache__ --exclude '*.pyc')

log() { printf '[hostess7-deploy] %s\n' "$*"; }

ssh -o ConnectTimeout=15 -p "$PORT" -i "$SSH_KEY" ubuntu@127.0.0.1 \
  'sudo mkdir -p /opt/ammoos/ammoos/NewLatest/Hostess7 && sudo chown -R ubuntu:ubuntu /opt/ammoos/ammoos/NewLatest/Hostess7'

log "rsync Hostess7 1.0.7h -> :$PORT ($NODE_ID)"
rsync -a -e "ssh -p $PORT -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
  "${H7_EXCLUDES[@]}" \
  "$H7/" "ubuntu@127.0.0.1:/opt/ammoos/ammoos/NewLatest/Hostess7/"

if [[ -d "$NL/hostess7-training-viewer" ]]; then
  log "rsync hostess7-training-viewer -> :$PORT"
  rsync -a -e "ssh -p $PORT -i $SSH_KEY -o StrictHostKeyChecking=accept-new" \
    "${TV_EXCLUDES[@]}" \
    "$NL/hostess7-training-viewer/" \
    "ubuntu@127.0.0.1:/opt/ammoos/ammoos/NewLatest/hostess7-training-viewer/"
fi

log "bootstrap Hostess7 war stack on :$PORT"
ssh -p "$PORT" -i "$SSH_KEY" ubuntu@127.0.0.1 bash -s <<REMOTE
set -euo pipefail
export SG_ROOT=/opt/ammoos/ammoos
export NEXUS_INSTALL_ROOT=/opt/ammoos/ammoos/NewLatest
export NEXUS_STATE_DIR=/opt/ammoos/ammoos/NewLatest/.nexus-state
export GROK_LAB_WORLD_NODE=1
export GROK_LAB_NODE_ID=$NODE_ID
export GROK_LAB_NODE_REGION=$REGION
export HOSTESS7_LICENSE_MODE=war
export HOSTESS7_WAR_READY=1
export AML_BUILD=0
export HOSTESS7_WEB_PORT=8080
export GROK16_ROOT="\$NEXUS_INSTALL_ROOT/Grok16"
export GPY16_ROOT="\$GROK16_ROOT/python"
export GROKPY_ROOT="\$GPY16_ROOT"
export PYTHONG_ROOT="\$GROK16_ROOT"
export PATH="\$GROK16_ROOT/bin:/usr/bin:/bin:\$PATH"
H7="\$NEXUS_INSTALL_ROOT/Hostess7"
export HOSTESS7_ROOT="\$H7"
export HOSTESS7_BRAIN_STATE="\$H7/brain/state"
cd "\$H7"
chmod +x Hostess7.sh scripts/*.py 2>/dev/null || true
python3 -m pip install --user -q flask 2>/dev/null \
  || python3 -m pip install --user --break-system-packages -q flask 2>/dev/null \
  || true
PIDF="\$HOSTESS7_BRAIN_STATE/hostess7-web.pid"
LOG="\$HOSTESS7_BRAIN_STATE/hostess7-web.log"
mkdir -p "\$(dirname "\$LOG")"
if [[ -f "\$PIDF" ]]; then kill "\$(cat "\$PIDF")" 2>/dev/null || true; rm -f "\$PIDF"; fi
nohup python3 "\$H7/scripts/hostess7_web.py" >>"\$LOG" 2>&1 &
echo \$! >"\$PIDF"
for i in \$(seq 1 30); do
  h7=\$(curl -sf -o /dev/null -w '%{http_code}' "http://127.0.0.1:\${HOSTESS7_WEB_PORT}/health" 2>/dev/null || echo 000)
  [[ "\$h7" == "200" ]] && break
  sleep 1
done
printf '[hostess7-deploy] web pid=%s health=%s\n' "\$(cat "\$PIDF")" "\$h7"
truth=\$(PYTHONPATH="\$H7/src:\$H7/scripts" python3 -m hostess7.cohesion truth 2>&1 | tail -5 || echo truth-fail)
printf '[hostess7-deploy] validate-truth: %s\n' "\$truth"
field=\$(curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1:9477/field 2>/dev/null || echo down)
h7=\$(curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/ 2>/dev/null || echo down)
eye=\$(curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1:9479/api/health 2>/dev/null || echo down)
ver=\$(grep -m1 '"version"' dist/hostess7-1.0.7h-rtx-linux-gnu-x86_64/manifest.json 2>/dev/null || echo unknown)
printf '[hostess7-deploy] node=%s field=%s hostess7=%s final_eye=%s version=%s\n' "$NODE_ID" "\$field" "\$h7" "\$eye" "\$ver"
if [[ "\$field" != "200" || "\$h7" != "200" ]]; then
  echo '[hostess7-deploy] FAIL — stack not operational' >&2
  exit 1
fi
REMOTE

log "operational :$PORT $NODE_ID"