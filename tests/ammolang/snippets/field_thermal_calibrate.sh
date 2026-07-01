#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-thermal-calibrate.py" ]]
  grep -q 'speed_impact' "${ROOT}/data/field-thermal-guard-doctrine.json"
  grep -q 'max_ops_per_second_at_budget' "${ROOT}/lib/field-thermal-guard.py"
  tmp_state="$(mktemp -d)"
out=$("$PY" "${ROOT}/lib/field-thermal-calibrate.py" calibrate 2>/dev/null 2>/dev/null || true); grep -q 'joules_per_field_op'
out=$("$PY" "${ROOT}/lib/field-thermal-calibrate.py" calibrate 2>/dev/null 2>/dev/null || true); grep -q 'none_under_normal_load'
  rm -rf "$tmp_state"
