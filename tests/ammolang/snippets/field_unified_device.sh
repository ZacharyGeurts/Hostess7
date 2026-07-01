#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-unified-device.py" ]]
  [[ -f "${ROOT}/data/field-unified-device-doctrine.json" ]]
  grep -q 'one_field_whole_device' "${ROOT}/data/field-unified-device-doctrine.json"
  grep -q 'kilroy_kernel_first' "${ROOT}/data/field-unified-device-doctrine.json"
  grep -q 'unified_device_field' "${ROOT}/lib/field-underlay.py"
  tmp_state="$(mktemp -d)"
out=$("$PY" "${ROOT}/lib/field-unified-device.py" board 2>/dev/null 2>/dev/null || true); grep -q '"one_field": true'
  [[ -f "${tmp_state}/field-unified-device.json" ]]
  grep -q 'kilroy_kernel' "${tmp_state}/field-unified-device.json"
  grep -q 'motherboard' "${tmp_state}/field-unified-device.json"
  grep -q 'fcc' "${tmp_state}/field-unified-device.json"
  rm -rf "$tmp_state"
