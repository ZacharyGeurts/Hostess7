#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-g16-universal-combinatronic.py" ]]
  [[ -f "${ROOT}/lib/g16-combinatronic-rebalance.py" ]]
  [[ -f "${ROOT}/data/field-g16-universal-combinatronic-doctrine.json" ]]
  [[ -f "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/scripts/g16-combinatronic-rebalance.sh" ]]
  grep -q 'g16_universal' "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/data/g16-field-combinatorics-doctrine.json"
  grep -q '_g16_universal_slice' "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/lib/field_combinatorics.py"
  grep -q 'g16_universal' "${ROOT}/lib/field-plate-combinatorics-bridge.py"
  grep -q 'g16_optimal' "${ROOT}/lib/field-combinatorics-studio.py"
  grep -q '/api/g16/universal-combinatronic' "${ROOT}/lib/threat-panel-http.py"
  grep -q '"basic"' "${ROOT}/data/field-program-combinatronic-seed.json"
  grep -q '"pascal"' "${ROOT}/data/field-program-combinatronic-seed.json"
  grep -q '"qbasic"' "${ROOT}/data/field-program-combinatronic-seed.json"
  grep -q '"turbo_pascal"' "${ROOT}/data/field-program-combinatronic-seed.json"
  grep -q '"turbo_pascal"' "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/data/grok16-languages.json"
  grep -q '"ammolang"' "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/data/grok16-languages.json"
  tmp_state="$(mktemp -d)"
  out="$(mktemp)"
  aml_py "field-g16-universal-combinatronic.py" combinatronic >"$out" 2>/dev/null || true
  grep -q 'field-g16-universal-combinatronic/v1' "$out"
  aml_py "g16-combinatronic-rebalance.py" connect >"$out" 2>/dev/null || true
  grep -q '"action": "connect"' "$out"
  aml_py "field-program-combinatronic.py" boil qbasic PRINT >"$out" 2>/dev/null || true
  grep -q '"canonical": "io"' "$out"
  aml_py "field-program-combinatronic.py" boil turbo_pascal CRT >"$out" 2>/dev/null || true
  grep -q '"canonical": "import"' "$out"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    python3 "$sg/Grok16/lib/field_combinatorics.py" publish >"$out" 2>/dev/null
  grep -q 'g16_universal' "$out"
  rm -f "$out"
  rm -rf "$tmp_state"
