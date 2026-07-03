#!/usr/bin/env bash
set -euo pipefail
ROOT="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state-ci}"
mkdir -p "$NEXUS_STATE_DIR"

python3 -m py_compile "$ROOT/lib/field-dns-table-clean.py"
chmod +x "$ROOT/scripts/dns-clean-tables.sh"

clean="$(python3 "$ROOT/lib/field-dns-table-clean.py" clean)"
python3 -c "import json,sys; d=json.loads(sys.argv[1]); assert d.get('mode')=='clean'; assert d.get('ok'); assert 'clear' not in (d.get('warning') or '')" "$clean"

blocked="$(python3 "$ROOT/lib/field-dns-table-clean.py" clear 2>/dev/null || true)"
python3 -c "import json,sys; d=json.loads(sys.argv[1]); assert d.get('error')=='clear_requires_i_know'" "$blocked"

grep -q 'field-dns-clear.signal' "$ROOT/lib/field-dns.py"
grep -q 'clean ≠ clear' "$ROOT/data/field-dns-table-clean-doctrine.json" || grep -q 'clean' "$ROOT/data/field-dns-table-clean-doctrine.json"
echo "dns_table_clean_smoke=ok"