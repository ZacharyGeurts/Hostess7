#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-predictive-meld.py" ]]
  [[ -f "${ROOT}/data/field-predictive-meld-doctrine.json" ]]
  grep -q 'predictive_meld' "${ROOT}/lib/field-plate-meld.py"
  grep -q 'merge_balance_gate' "${ROOT}/lib/field-combinatronic-balance.py"
  grep -q 'predictive_meld' "${ROOT}/data/field-combinatronic-balance-doctrine.json"
  grep -q 'predictive_meld' "${ROOT}/data/field-predictive-meld-doctrine.json"
  tmp_state="$(mktemp -d)"
out=$("$PY" "${ROOT}/lib/field-predictive-meld.py" verify 2>/dev/null || true); grep -q '"ok": true'
out=$("$PY" "${ROOT}/lib/field-predictive-meld.py" predict 2>/dev/null || true); grep -q 'field-predictive-meld/v1'
out=$("$PY" "${ROOT}/lib/field-predictive-meld.py" fingerprint 2>/dev/null || true); grep -q 'field-predictive-meld-fingerprint'
out=$("$PY" "${ROOT}/lib/field-predictive-meld.py" record --refresh --ms 12 2>/dev/null || true); grep -q 'predictive_refresh_recorded'
out=$("$PY" "${ROOT}/lib/field-predictive-meld.py" predict 2>/dev/null || true); grep -q 'predictive_stable'
out=$("$PY" "${ROOT}/lib/field-combinatronic-balance.py" gate 2>/dev/null || true); grep -q 'predictive_meld'
