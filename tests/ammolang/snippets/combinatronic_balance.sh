#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

[[ -f "${ROOT}/lib/field-combinatronic-balance.py" ]]
[[ -f "${ROOT}/data/field-combinatronic-balance-doctrine.json" ]]
grep -q 'combinatronic_balance' "${ROOT}/lib/field-panel-parallel.py"
grep -q '/api/combinatronic/balance' "${ROOT}/lib/threat-panel-http.py"
grep -q '/api/combinatronic/balance' "${ROOT}/Queen/lib/queen-world.py"
grep -q 'gate_refresh' "${ROOT}/lib/field-ironclad-chips-combinatorics.py"
grep -q 'gate_refresh' "${ROOT}/lib/field-program-combinatronic.py"
grep -q 'gate_refresh' "${ROOT}/lib/field-combinamatrix.py"
grep -q 'gate_refresh' "${ROOT}/lib/field-g16-universal-combinatronic.py"
grep -q 'combinatoric_entry' "${ROOT}/lib/field-combinatronic-balance.py"
grep -q 'read_content_balance' "${ROOT}/lib/field-combinatronic-balance.py"
grep -q 'balance_id' "${ROOT}/lib/field-combinatronic-balance.py"
grep -q 'balance_as_best_identifier' "${ROOT}/data/field-combinatronic-balance-doctrine.json"
grep -q 'combinatronic_balance' "${ROOT}/lib/h7-library-bridge.py"
grep -q 'sync_all_entries' "${ROOT}/lib/field-combinatronic-balance.py"
grep -q 'entry_batteries' "${ROOT}/data/field-combinatronic-balance-doctrine.json"
grep -q 'combinatoric_entry' "${ROOT}/lib/field-combinatronics-growth.py"
grep -q 'combinatoric_entry' "${ROOT}/lib/field-extensive-library.py"

tmp_state="$(aml_tmp_state)"
run_py() {
  local state_dir="$1"
  shift
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$state_dir" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" AML_INLINE=1 AML_TEST_DIRECT="${AML_TEST_DIRECT:-0}" \
    "$PY" "$@"
}

out=$(run_py "$tmp_state" "${ROOT}/lib/field-combinatronic-balance.py" verify 2>/dev/null || true); grep -q '"ok": true' <<<"$out"
out=$(run_py "$tmp_state" "${ROOT}/lib/field-combinatronic-balance.py" content openstax_biology --format textbook --collection textbooks 2>/dev/null || true); grep -q 'field-combinatronic-content-balance' <<<"$out"
out=$(run_py "$tmp_state" "${ROOT}/lib/field-combinatronic-balance.py" identify openstax_biology --format textbook --collection textbooks 2>/dev/null || true); grep -q 'CBAL-' <<<"$out"
run_py "$tmp_state" "${ROOT}/lib/field-chip-battery.py" publish >/dev/null 2>&1 || true
run_py "$tmp_state" "${ROOT}/lib/field-program-combinatronic.py" publish >/dev/null 2>&1 || true
out=$(run_py "$tmp_state" "${ROOT}/lib/g16-combinatronic-rebalance.py" rebalance --refresh 2>/dev/null || true); grep -q '"action": "rebalance"' <<<"$out"
out=$(run_py "$tmp_state" "${ROOT}/lib/g16-combinatronic-rebalance.py" rebalance 2>/dev/null || true); grep -q 'balanced_hold' <<<"$out"
out=$(run_py "$tmp_state" "${ROOT}/lib/field-chip-battery.py" combinatronic 2>/dev/null || true); grep -q '"combinatronic": true' <<<"$out"
out=$(run_py "$tmp_state" "${ROOT}/lib/field-combinatronic-balance.py" panel 2>/dev/null || true); grep -q '"optimized_combinatronic": true' <<<"$out"
out=$(run_py "$tmp_state" "${ROOT}/lib/field-combinatronic-balance.py" sync 2>/dev/null || true); grep -q '"synchronous": true' <<<"$out"
out=$(run_py "$tmp_state" "${ROOT}/lib/field-combinatronic-balance.py" fingerprint 2>/dev/null || true); grep -q '"entry_base":' <<<"$out"
rm -rf "$tmp_state"