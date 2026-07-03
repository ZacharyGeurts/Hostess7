#!/usr/bin/env bash
# Sovereign Truth DNS + GitHub path harden smoke (no live push required)
set -euo pipefail
ROOT="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state-ci}"
mkdir -p "$NEXUS_STATE_DIR"

python3 -m py_compile "$ROOT/lib/field-dns-resolve.py"
python3 -m py_compile "$ROOT/lib/field-github-path-harden.py"
python3 -m py_compile "$ROOT/Hostess7/scripts/hostess7_secure_git.py"

python3 -c "import json; d=json.load(open('$ROOT/data/field-github-path-harden-doctrine.json')); assert d.get('sovereign_dns',{}).get('truth_host')=='127.0.0.1'"
python3 "$ROOT/lib/field-dns-resolve.py" status | grep -q 'field-dns-resolve/v1'

dns="$(python3 -c "
import importlib.util, json
from pathlib import Path
root = Path('$ROOT')
spec = importlib.util.spec_from_file_location('harden', root / 'lib/field-github-path-harden.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
doc = json.loads((root / 'data/field-github-path-harden-doctrine.json').read_text())
print(json.dumps(mod.dns_crosscheck(doc)))
")"
python3 -c "import json,sys; d=json.loads(sys.argv[1]); assert d.get('authority')=='truth_dns'; assert 'hosts' in d" "$dns"

grep -q 'ensure_truth_dns' "$ROOT/scripts/github-unflake.sh"
grep -q 'ensure_truth_dns' "$ROOT/scripts/github-lanes.sh"
grep -q 'field-dns-resolve' "$ROOT/Hostess7/scripts/hostess7_secure_git.py"
grep -q 'field-dns-resolve' "$ROOT/lib/field-github-path-harden.py"

echo "github_sovereign_dns_smoke=ok"