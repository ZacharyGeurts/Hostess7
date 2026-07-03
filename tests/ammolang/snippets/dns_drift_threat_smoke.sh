#!/usr/bin/env bash
# DNS drift threat + servers-updated audit smoke
set -euo pipefail
ROOT="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state-ci}"
mkdir -p "$NEXUS_STATE_DIR"

python3 -m py_compile "$ROOT/lib/field-dns-drift-threat.py"
python3 -c "import json; d=json.load(open('$ROOT/data/field-dns-drift-threat-doctrine.json')); assert d.get('drift_as_threat') is True"

panel="$(python3 "$ROOT/lib/field-dns-drift-threat.py" panel)"
python3 -c "import json,sys; d=json.loads(sys.argv[1]); assert 'drift' in d; assert 'servers_updated' in d" "$panel"

grep -q 'DNS_DRIFT_THREAT\|DNS drift threat' "$ROOT/lib/field-github-path-harden.py"
grep -q 'field-dns-drift-threat' "$ROOT/lib/field-dns.sh"
grep -q 'dns_drift_threat' "$ROOT/data/field-botnet-dns-dhcp-doctrine.json"

echo "dns_drift_threat_smoke=ok"