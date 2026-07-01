#!/usr/bin/env bash
# Scan non-Field-1 fields → hostile → bring to Field 1 on world nodes.
set -uo pipefail

NL="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
SG="${SG_ROOT:-$(cd "$NL/.." && pwd)}"
STATE="${NEXUS_STATE_DIR:-$NL/.nexus-state}"
PY="${GROK_LAB_PY:-python3}"
REGION="${GROK_LAB_NODE_REGION:-local}"
NODE_ID="${GROK_LAB_NODE_ID:-node-local}"

log() { printf '[field-one-bring] %s\n' "$*"; }

export SG_ROOT="$SG" NEXUS_INSTALL_ROOT="$NL" NEXUS_STATE_DIR="$STATE"
export FIELD_ONE_BRING_STORAGE_ONLY=1

if [[ -x "$NL/Grok16/bin/gpy-16" ]]; then
  export PATH="$NL/Grok16/bin:$PATH"
  PY="$NL/Grok16/bin/gpy-16"
fi

log "scan non-Field-1 → hostile → Field 1 (region=$REGION node=$NODE_ID)"
if [[ -f "$NL/lib/field-one-hostile-scan.py" ]]; then
  "$PY" "$NL/lib/field-one-hostile-scan.py" 2>/dev/null | tail -20 || true
fi

# Home sanctuary pushes canonical kill state to perimeter after bring
if [[ "$NODE_ID" == "node-local" || "$REGION" == "local" ]]; then
  HOSTILE="$NL/.nexus-state/field-hostile.tsv"
  REGISTRY="$NL/.nexus-state/kill-rekill-registry.json"
  NODES="$NL/GrokLab/deploy/world-nodes.json"
  SSH_KEY="${GROK_LAB_SSH_KEY:-$NL/GrokLab/deploy/world-ssh/id_ed25519}"
  if [[ -f "$HOSTILE" && -f "$NODES" ]]; then
    while IFS= read -r line; do
      port=$(echo "$line" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('ssh_port',0))" 2>/dev/null)
      enabled=$(echo "$line" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print('1' if d.get('enabled') and d.get('ssh') else '0')" 2>/dev/null)
      [[ "$enabled" != "1" || "$port" == "0" ]] && continue
      timeout 8 scp -P "$port" -i "$SSH_KEY" \
        -o StrictHostKeyChecking=accept-new -o ConnectTimeout=4 \
        "$HOSTILE" "$REGISTRY" \
        "ubuntu@127.0.0.1:/opt/ammoos/ammoos/NewLatest/.nexus-state/" 2>/dev/null || true
    done < <(python3 -c "
import json
from pathlib import Path
doc=json.loads(Path('$NODES').read_text())
for n in doc.get('nodes',[]):
    print(json.dumps(n))
")
    log "canonical Field 1 kill state pushed to world nodes"
  fi
fi

log "Field 1 bring complete"