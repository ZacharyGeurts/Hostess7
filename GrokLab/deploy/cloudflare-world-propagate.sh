#!/usr/bin/env bash
# Push Cloudflare tunnel arm to every enabled world node (SSH + token sync).
set -uo pipefail

DEPLOY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NL="${NEXUS_INSTALL_ROOT:-$(cd "$DEPLOY/../../.." && pwd)}"
NODES="$DEPLOY/world-nodes.json"
PY="${GROK_LAB_PY:-python3}"
SSH_KEY="${GROK_LAB_SSH_KEY:-$DEPLOY/world-ssh/id_ed25519}"

log() { printf '[cloudflare-propagate] %s\n' "$*"; }

TOKEN_SRC="${CLOUDFLARE_TUNNEL_TOKEN:-}"
[[ -z "$TOKEN_SRC" && -f "$DEPLOY/cloudflare/tunnel.token" ]] && TOKEN_SRC=$(tr -d ' \n' <"$DEPLOY/cloudflare/tunnel.token")

log "=== propagate Cloudflare perimeter to world nodes ==="

# Local home sanctuary first
export GROK_LAB_NODE_ID=node-local GROK_LAB_NODE_REGION=local
bash "$DEPLOY/cloudflare-world-tunnel.sh" 2>&1 | tail -6

if [[ ! -f "$NODES" ]]; then
  log "no world-nodes.json"
  exit 0
fi

while IFS= read -r line; do
  id=$(echo "$line" | "$PY" -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('id',''))")
  ssh_host=$(echo "$line" | "$PY" -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('ssh',''))")
  port=$(echo "$line" | "$PY" -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('ssh_port',22))")
  region=$(echo "$line" | "$PY" -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('region',''))")
  enabled=$(echo "$line" | "$PY" -c "import sys,json; d=json.loads(sys.stdin.read()); print('1' if d.get('enabled') else '0')")
  [[ "$enabled" != "1" || -z "$ssh_host" ]] && continue

  log "node $id :$port ($region)"
  if ! scp -P "$port" -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new \
    "$DEPLOY/cloudflare-world-tunnel.sh" \
    "$DEPLOY/cloudflare-world-config.json" \
    "ubuntu@127.0.0.1:/opt/ammoos/ammoos/NewLatest/GrokLab/deploy/" 2>/dev/null; then
    scp -P "$port" -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new \
      "$DEPLOY/cloudflare-world-tunnel.sh" \
      "$DEPLOY/cloudflare-world-config.json" \
      "ubuntu@127.0.0.1:/tmp/" 2>/dev/null || { log "  skip $id (scp failed)"; continue; }
    ssh -p "$port" -i "$SSH_KEY" ubuntu@127.0.0.1 \
      'sudo mkdir -p /opt/ammoos/ammoos/NewLatest/GrokLab/deploy/cloudflare && sudo cp /tmp/cloudflare-world-*.sh /tmp/cloudflare-world-*.json /opt/ammoos/ammoos/NewLatest/GrokLab/deploy/ 2>/dev/null; sudo chown -R ubuntu:ubuntu /opt/ammoos 2>/dev/null' 2>/dev/null || true
  fi

  if [[ -n "$TOKEN_SRC" ]]; then
    ssh -p "$port" -i "$SSH_KEY" ubuntu@127.0.0.1 \
      "mkdir -p /opt/ammoos/ammoos/NewLatest/GrokLab/deploy/cloudflare && printf '%s' '$TOKEN_SRC' > /opt/ammoos/ammoos/NewLatest/GrokLab/deploy/cloudflare/tunnel.token && chmod 600 /opt/ammoos/ammoos/NewLatest/GrokLab/deploy/cloudflare/tunnel.token" 2>/dev/null || true
  fi

  # Ship cloudflared binary if node lacks it
  if [[ -x "$DEPLOY/cloudflare/bin/cloudflared" ]]; then
    ssh -p "$port" -i "$SSH_KEY" ubuntu@127.0.0.1 'mkdir -p /opt/ammoos/ammoos/NewLatest/GrokLab/deploy/cloudflare/bin' 2>/dev/null || true
    scp -P "$port" -i "$SSH_KEY" "$DEPLOY/cloudflare/bin/cloudflared" \
      "ubuntu@127.0.0.1:/opt/ammoos/ammoos/NewLatest/GrokLab/deploy/cloudflare/bin/" 2>/dev/null || true
  fi

  ssh -p "$port" -i "$SSH_KEY" ubuntu@127.0.0.1 \
    "cd /opt/ammoos/ammoos/NewLatest 2>/dev/null || exit 0; \
     SG_ROOT=/opt/ammoos/ammoos NEXUS_INSTALL_ROOT=/opt/ammoos/ammoos/NewLatest \
     NEXUS_STATE_DIR=/opt/ammoos/ammoos/NewLatest/.nexus-state \
     GROK_LAB_NODE_ID=$id GROK_LAB_NODE_REGION=$region \
     CLOUDFLARED_BIN=/opt/ammoos/ammoos/NewLatest/GrokLab/deploy/cloudflare/bin/cloudflared \
     bash GrokLab/deploy/cloudflare-world-tunnel.sh" 2>&1 | tail -4 || log "  skip $id (not deployed yet)"
done < <("$PY" -c "
import json
from pathlib import Path
doc=json.loads(Path('$NODES').read_text())
for n in doc.get('nodes',[]):
    print(json.dumps(n))
")

log "propagation pass complete"