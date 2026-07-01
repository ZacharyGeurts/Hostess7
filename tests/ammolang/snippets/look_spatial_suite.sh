#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
# Look spatial — pair different views; alarm same view at multiple locations.
MOD="${ROOT}/lib/field-look-spatial.py"
[[ -f "$MOD" ]]
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
printf 'view-alpha-pixels' > "$tmp/a.png"
printf 'view-beta-pixels-xx' > "$tmp/b.png"
# Different views at different locations — no alarm
r1=$("$PY" "$MOD" register feed-left left-lane "$tmp/a.png")
echo "$r1" | grep -q '"ok": true'
echo "$r1" | grep -q '"alarm"' && exit 1 || true
r2=$("$PY" "$MOD" register feed-right right-lane "$tmp/b.png")
echo "$r2" | grep -q '"ok": true'
# Pair the two look lanes
pair=$("$PY" "$MOD" pair feed-left feed-right)
echo "$pair" | grep -q '"paired": true'
echo "$pair" | grep -q 'different_views'
# Same view at second location — must alarm
r3=$("$PY" "$MOD" register feed-right right-lane "$tmp/a.png")
echo "$r3" | grep -q '"alarm": true'
echo "$r3" | grep -q 'same_view_multi_location\|other_locations'
status=$("$PY" "$MOD" status)
echo "$status" | grep -q 'field-look-spatial-panel'
echo "$status" | grep -q '"pair_count": 1'
