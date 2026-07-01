#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
# Final Eye GPS nav — sub-micron place, heading, azimuth, bearing on capture meta.
MOD="${ROOT}/lib/final-eye-gps-nav.py"
ZOCR_NAV="$ROOT/.pages-hub-Final_Eye/zocr_nav.py"
[[ -f "$MOD" ]]
[[ -f "$ZOCR_NAV" ]]
snap=$("$PY" "$MOD" snapshot)
echo "$snap" | grep -q '"schema": "final-eye-nav/v1"'
echo "$snap" | grep -q '"ok": true'
echo "$snap" | grep -q '"lat"'
echo "$snap" | grep -q '"lon"'
echo "$snap" | grep -q '"lat_i"'
echo "$snap" | grep -q '"heading_deg"\|"course_deg"\|"azimuth_deg"'
echo "$panel" | grep -q 'final-eye-nav-panel'
echo "$panel" | grep -q '"receipt_fields"'
"$PY" "$MOD" set-heading 127.5 >/dev/null
after=$("$PY" "$MOD" snapshot)
echo "$after" | grep -q '"heading_deg": 127.5'
enriched=$("$PY" "$MOD" enrich '{"schema":"test","eye":{"eyes":[{"role":"center","offset_x":4,"perceived":true}]}}')
echo "$enriched" | grep -q '"nav"'
echo "$enriched" | grep -q '"lat"'
echo "$enriched" | grep -q '"azimuth_deg"'
wrap=$("$PY" "$ZOCR_NAV" snapshot)
echo "$wrap" | grep -q '"ok": true'
