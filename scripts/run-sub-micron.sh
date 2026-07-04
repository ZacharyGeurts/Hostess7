#!/usr/bin/env bash
# Sub-micron placement + sub-microsecond timing — run hard now.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-field-drive/nexus-field/state}"
export FIELD_RACK_ID="${FIELD_RACK_ID:-rack-$(hostname -s 2>/dev/null || echo local)}"
PY="${PYTHON:-python3}"

log() { printf '[sub-micron] %s\n' "$*"; }

log "sub-microsecond bench + sub-micron precision field"
"$PY" "$ROOT/lib/field-sub-micron-timing.py" run | "$PY" -c "
import json,sys
d=json.load(sys.stdin)
sp=d.get('spatial',{})
tm=d.get('temporal',{})
b=tm.get('bench',{})
print('  sub_micron LSB ~0.11nm · placed', (sp.get('precision_field') or {}).get('placed'))
print('  sub_µs capable:', tm.get('sub_microsecond'), 'mono min_us', (b.get('mono_us') or {}).get('min'))
print('  cycle_us', tm.get('cycle_elapsed_us'), 'rack', (d.get('rack') or {}).get('field_id'))
"

log "precision field + timing panels live"
log "  api /api/field-sub-micron-timing · /api/precision-field · /api/gps-precision"