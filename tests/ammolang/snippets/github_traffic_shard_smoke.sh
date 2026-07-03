#!/usr/bin/env bash
# GitHub traffic shard — 90% field offload smoke
set -euo pipefail
ROOT="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state-ci}"
mkdir -p "$NEXUS_STATE_DIR"

python3 -m py_compile "$ROOT/lib/field-github-traffic-shard.py"
python3 -c "import json; d=json.load(open('$ROOT/data/field-github-traffic-shard-doctrine.json')); assert d.get('offload_target_pct')>=85"

panel="$(python3 "$ROOT/lib/field-github-traffic-shard.py" panel)"
python3 -c "import json,sys; d=json.loads(sys.argv[1]); assert d.get('schema')=='field-github-traffic-shard-panel/v1'; assert d.get('offload_target_pct',0)>=85" "$panel"

grep -q 'field-github-traffic-shard' "$ROOT/lib/field-github-legacy.py"
grep -q 'field-github-traffic-shard' "$ROOT/lib/field-github-resilience.py"
grep -q 'keepalive_allowed' "$ROOT/lib/field-internet-unified.py"
grep -q '120000' "$ROOT/Hostess7/docs/pages-hostess7-interaction-wire.js"

echo "github_traffic_shard_smoke=ok"