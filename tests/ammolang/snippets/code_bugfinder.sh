#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-code-bugfinder.py" ]]
  [[ -f "${ROOT}/data/field-code-bugfinder-doctrine.json" ]]
  [[ -f "${ROOT}/data/field-media-codec-doctrine.json" ]]
  grep -q '/api/bugfinder' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/bugfinder/ironclad-cycle' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'ironclad_bugfix_cycle' "${ROOT}/lib/field-code-bugfinder.py"
  grep -q 'code_bugfinder' "${ROOT}/lib/field-plate-meld.py"
  grep -q 'truth_compare_high_rate' "${ROOT}/lib/field-code-bugfinder.py"
out=$("$PY" "${ROOT}/lib/field-code-bugfinder.py" json 2>/dev/null || true); grep -q 'field-code-bugfinder-panel/v1'
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$(mktemp -d)" SG_ROOT="$sg" HOSTESS7_ROOT="$ROOT/Hostess7" \
    aml_py "field-code-bugfinder.py" text \
      'password = "hardcoded_secret"; eval(user_input)' \
    | grep -q 'truth_compares_per_sec'
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$(mktemp -d)" SG_ROOT="$sg" HOSTESS7_ROOT="$ROOT/Hostess7" \
    aml_py "field-code-bugfinder.py" scan "${ROOT}/lib/field-code-bugfinder.py" --max 32 \
    | grep -q '"bug_count"'
