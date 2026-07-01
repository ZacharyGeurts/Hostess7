#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
# H7s global suite — in-place disguise, no sidecars, kernel boot guard.
H7S="${ROOT}/lib/field-h7s-format.py"
ADOPT="${ROOT}/lib/field-h7s-adopt.py"
CLEAN="${ROOT}/lib/field-h7s-cleanup.py"
BUNDLE="${ROOT}/lib/field-h7s-desktop-bundle.py"
[[ -f "$H7S" && -f "$ADOPT" && -f "$CLEAN" ]]
# Family verify — no double-wrap
out=$("$PY" "$H7S" verify)
echo "$out" | grep -q '"ok": true'
echo "$out" | grep -q 'h7s->h7s'
# In-place pack + properties disguise — same .json extension, no sidecar
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
echo '{"schema":"h7s-test/v1","modules":{"a":1}}' > "$tmp/sample.json"
pack=$("$PY" "$H7S" pack "$tmp/sample.json" "$tmp/sample.json")
echo "$pack" | grep -q '"ok": true'
[[ ! -f "$tmp/sample.json.h7s" ]]
props=$("$PY" "$H7S" properties "$tmp/sample.json")
echo "$props" | grep -q 'h7s/1'
echo "$props" | grep -q 'disguise_identical'
readback=$("$PY" "${ROOT}/lib/field-h7s-fs.py" read "$tmp/sample.json")
echo "$readback" | grep -q '"ok": true'
# Kernel boot guard — KILROY build path excluded, not the whole stack
guard=$("$PY" "$ADOPT" guard "$ROOT/KILROY/build/vmlinuz")
echo "$guard" | grep -q '"kernel_boot_excluded": true'
guard2=$("$PY" "$ADOPT" guard "$tmp/sample.json")
echo "$guard2" | grep -q '"can_adopt"'
# Desktop bundle live + first/last/live_feed schema
status=$("$PY" "$BUNDLE" status)
echo "$status" | grep -q '"live": true'
echo "$status" | grep -q 'desktop_condenser\|h7s/1\|"format": "h7s/1"'
# Cleanup audit runs
audit=$("$PY" "$CLEAN" audit)
echo "$audit" | grep -q 'field-h7s-cleanup-audit'
echo "$audit" | grep -q '"bundle_live": true'
# Hostess 7 + Ironclad lane orchestrator
LANE="${ROOT}/lib/field-h7s-lane.py"
[[ -f "$LANE" ]]
lane=$("$PY" "$LANE" status)
echo "$lane" | grep -q 'field-h7s-lane/v1'
echo "$lane" | grep -q 'kilroy_kernel_boot_excluded'
h7=$("$PY" "$LANE" hostess7)
echo "$h7" | grep -q '"lane": "hostess7"'
# H7s filesystem resolve — in-place at original extension
FS="${ROOT}/lib/field-h7s-fs.py"
[[ -f "$FS" ]]
fs=$("$PY" "$FS" resolve "$NEXUS_STATE_DIR/threat-panel.json")
echo "$fs" | grep -q 'field-h7s-fs-resolve'
echo "$fs" | grep -q '"sidecars": false'
echo "$fs" | grep -q 'h7s_in_place\|h7s_active'
# Migrate legacy sidecars if any
"$PY" "$CLEAN" migrate-sidecars --apply >/dev/null || true
# OCR cleanup audit
ocr_audit=$("$PY" "$CLEAN" audit-ocr)
echo "$ocr_audit" | grep -q 'field-h7s-ocr-cleanup-audit'
# Prune stale OCR feeds
prune=$("$PY" "$BUNDLE" prune-ocr)
echo "$prune" | grep -q '"ok": true'
grep -q 'sidecars' "$ROOT/data/field-h7s-global-doctrine.json"
grep -q 'in_place' "${ROOT}/lib/field-h7s-adopt.py"
