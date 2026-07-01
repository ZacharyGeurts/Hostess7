#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-chips-program-usage.py" ]]
  [[ -f "${ROOT}/data/field-chips-program-usage-doctrine.json" ]]
  [[ -f "${ROOT}/data/field-chips-program-usage-seed.json" ]]
  grep -q 'chips_program_usage' "${ROOT}/lib/field-panel-parallel.py"
  grep -q '/api/chips/usage' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/chips/usage' "${ROOT}/Queen/lib/queen-world.py"
  grep -q 'chips_usage' "${ROOT}/Queen/lib/queen-kilroy.py"
  grep -q 'chips_usage' "${ROOT}/Queen/lib/queen-desktop.py"
  grep -q 'kilroy_integration' "${ROOT}/data/field-chips-program-usage-doctrine.json"
  tmp_state="$(mktemp -d)"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    aml_py "field-ironclad-chips-combinatorics.py" publish >/dev/null
out=$("$PY" "${ROOT}/lib/field-chips-program-usage.py" resolve browser 2>/dev/null || true); grep -q 'field-chips-program-usage/v1' <<<"$out"
out=$("$PY" "${ROOT}/lib/field-chips-program-usage.py" kilroy 2>/dev/null || true); grep -q '"program_id": "kilroy"' <<<"$out"
out=$("$PY" "${ROOT}/lib/field-chips-program-usage.py" publish 2>/dev/null || true); grep -q 'field-chips-program-usage-registry/v1' <<<"$out"
  rm -rf "$tmp_state"
