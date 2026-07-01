#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  tmp_state="$(mktemp -d)"
  [[ -f "${ROOT}/lib/iron-plate-organize.py" ]]
  [[ -f "${ROOT}/data/iron-plate-organize-doctrine.json" ]]
  grep -q 'iron_plate_organize' "${ROOT}/lib/field-plate-meld.py"
  grep -q 'iron_plate_organize' "${ROOT}/data/field-plate-meld-doctrine.json"
  grep -q 'iron_plate_organize' "${ROOT}/lib/field-panel-parallel.py"
  grep -q '/api/iron-plate/organize' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'composite_bsp' "${ROOT}/data/iron-plate-organize-doctrine.json"
  grep -q 'ironclad_chain' "${ROOT}/data/iron-plate-organize-doctrine.json"
  grep -q '_ironclad_chain_tree' "${ROOT}/lib/iron-plate-organize.py"
  [[ -f "${ROOT}/lib/iron-plate-spot-detector.py" ]]
  [[ -f "${ROOT}/data/iron-plate-spot-doctrine.json" ]]
  grep -q 'thermal_gate' "${ROOT}/lib/iron-plate-spot-detector.py"
  grep -q '_thermal_gate' "${ROOT}/lib/iron-plate-organize.py"
  grep -q 'iron_plate_spot' "${ROOT}/lib/field-plate-meld.py"
  grep -q '/api/iron-plate/spots' "${ROOT}/lib/threat-panel-http.py"
  [[ -f "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/lib/g16-iron-plate-spot-detector.py" ]]
  grep -q 'iron_plate_spot' "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/forge/ironclad_tools.py"
  grep -q 'organize_gain' "${ROOT}/lib/iron-plate-organize.py"
  grep -q 'c2_browser_embed' "${ROOT}/data/ironclad-meld-extensions.json"
  grep -q '_iron_plate_organize' "${ROOT}/lib/field-host-desktop.py"
  grep -q '"id": "iron_plate_organize"' "${ROOT}/data/ironclad-meld-extensions.json"
organize_out="$(mktemp)"
aml_py "iron-plate-organize.py" json >"$organize_out" 2>/dev/null || true
grep -q 'iron-plate-organize/v1' "$organize_out"
grep -q 'composite_bsp' "$organize_out"
out=$("$PY" "${ROOT}/lib/iron-plate-organize.py" apply-desktop 2>/dev/null || true); grep -q 'tray_icons' <<<"$out"
out=$("$PY" "${ROOT}/lib/iron-plate-motion-resolve.py" resolve 2>/dev/null || true); grep -q 'iron_plate_organize' <<<"$out"
rm -f "$organize_out"
