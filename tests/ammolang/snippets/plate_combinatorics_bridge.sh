#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-plate-combinatorics-bridge.py" ]]
  [[ -f "${ROOT}/lib/h7-library-truth.py" ]]
  [[ -f "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/lib/field_combinatorics.py" ]]
  [[ -f "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/lib/field_truth_blocks.py" ]]
  grep -q 'combinatorics_bridge' "${ROOT}/lib/field-panel-parallel.py"
  grep -q '_refresh_combinatorics_bridge' "${ROOT}/lib/field-plate-meld.py"
  grep -q 'combinatoric_tree_complete' "${ROOT}/lib/field-plate-meld.py"
  grep -q 'walk_tree_to_end' "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/lib/field_combinatorics.py"
  grep -q 'condense_plates' "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/lib/field_combinatorics.py"
  grep -q 'combinatorics-bridge/v2' "${ROOT}/lib/field-plate-combinatorics-bridge.py"
  grep -q 'c2_taskbar' "${ROOT}/lib/field-plate-combinatorics-bridge.py"
  grep -q 'combinatorics_rejected' "${ROOT}/lib/field-plate-combinatorics-bridge.py"
  grep -q 'read_last_good_panel' "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/lib/field_combinatorics.py"
  grep -q '_combinatorics_posture' "${ROOT}/lib/g16-compiler-sense-plate.py"
  grep -q '/api/library/truth' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'h7r-sentence' "${ROOT}/panel/assets/h7-reader.js"
  tmp_state="$(mktemp -d)"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" GROK16_ROOT="$sg/Grok16" SG_ROOT="$sg" \
    python3 "$sg/Grok16/lib/field_truth_blocks.py" publish 2>/dev/null | grep -m1 -q 'truth_block_count'
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" GROK16_ROOT="$sg/Grok16" SG_ROOT="$sg" \
    python3 "$sg/Grok16/lib/field_combinatorics.py" publish 2>/dev/null | grep -m1 -q 'combinatoric_tree'
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" GROK16_ROOT="$sg/Grok16" SG_ROOT="$sg" AML_INLINE="${AML_INLINE:-0}" \
    aml_py "field-plate-combinatorics-bridge.py" build 2>/dev/null | grep -m1 -q 'combinatoric_tree_complete'
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" HOSTESS7_ROOT="${HOSTESS7_ROOT:-$ROOT/Hostess7}" SG_ROOT="$sg" \
    aml_py "h7-library-truth.py" sentence network-security-field-guide 0 "Firewalls filter traffic." 2>/dev/null | grep -m1 -q 'verdict'
  rm -rf "$tmp_state"
