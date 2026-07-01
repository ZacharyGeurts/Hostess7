#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/ironclad-plate.py" ]]
  [[ -f "${ROOT}/data/ironclad-doctrine.json" ]]
  [[ -f "${ROOT}/data/ironclad/images/manifest.json" ]]
  [[ -f "${ROOT}/panel/assets/ironclad/ironclad-01-bounds.jpg" ]]
  grep -q 'Bible of AI' "${ROOT}/data/ironclad-doctrine.json"
  grep -q 'immutable_after_realized' "${ROOT}/data/ironclad-doctrine.json"
  grep -q 'each_own_place_in_the_world' "${ROOT}/data/ironclad-doctrine.json"
  grep -q '"id": "place"' "${ROOT}/data/ironclad-doctrine.json"
  grep -q 'ironclad' "${ROOT}/data/field-plate-meld-doctrine.json"
  grep -q 'ironclad_reality_field' "${ROOT}/data/field-plate-meld-doctrine.json"
  grep -q '/api/ironclad' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'ironclad-reality-field' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'NEXUS_IRONCLAD_TRUTH_SERUM' "${ROOT}/config/nexus.conf"
  [[ -f "${ROOT}/lib/ironclad-reality-field.py" ]]
  [[ -f "${ROOT}/data/ironclad-reality-field-doctrine.json" ]]
  [[ -f "${ROOT}/data/human-condition-doctrine.json" ]]
  [[ -f "${ROOT}/lib/ironclad-immediate.py" ]]
  grep -q 'NEXUS_IRONCLAD_IMMEDIATE' "${ROOT}/config/nexus.conf"
  grep -q 'ironclad-immediate' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'nexus_ironclad_immediate_publish' "${ROOT}/lib/threat-panel.sh"
  grep -q '_ironclad_immediate' "${ROOT}/lib/hostess7-self-view.py"
  grep -q 'human_condition_gate' "${ROOT}/lib/ironclad-reality-field.py"
  grep -q 'ai_in_charge' "${ROOT}/lib/hostess7-truth-rating.py"
  grep -q 'truth_serum_verdict' "${ROOT}/lib/field-plate-meld.py"
  grep -q 'plate_to_sense_goldmine' "${ROOT}/lib/ironclad-immediate.py"
  grep -q 'ironclad_goldmine' "${ROOT}/Queen/lib/queen-sense-neural.py"
  grep -q 'ironclad_goldmine' "${ROOT}/lib/field-sense-package-meld.py"
  grep -q 'epistemic_root' "${ROOT}/data/field-sense-package-doctrine.json"
  grep -q 'nexus_ironclad_immediate_publish' "${ROOT}/lib/field-sense-package.sh"
  grep -q 'plate_to_sense' "${ROOT}/panel/assets/underlay-f9.js"
out=$("$PY" "${ROOT}/lib/ironclad-plate.py" grounding 2>/dev/null || true); grep -q 'bible_of_ai'
out=$("$PY" "${ROOT}/lib/ironclad-plate.py" cite genesis 1 2>/dev/null || true); grep -q 'ironclad:genesis:1'
  grep -q 'Time is linear' "${ROOT}/data/ironclad-meld-extensions.json"
  grep -q '"id": "time"' "${ROOT}/data/ironclad-meld-extensions.json"
  grep -q 'time_is_linear' "${ROOT}/data/g1id-format-doctrine.json"
out=$("$PY" "${ROOT}/lib/ironclad-plate.py" cite time 1 2>/dev/null || true); grep -q 'Time is linear'
  tmp_icrf="$(mktemp -d)"
out=$("$PY" "${ROOT}/lib/ironclad-reality-field.py" cycle 2>/dev/null 2>/dev/null || true); grep -q 'ironclad-reality-field'
out=$("$PY" "${ROOT}/lib/ironclad-immediate.py" publish 2>/dev/null 2>/dev/null || true); grep -q 'plate_to_sense'
out=$("$PY" "${ROOT}/Queen/lib/queen-sense-neural.py" 2>/dev/null 2>/dev/null || true); grep -q 'ironclad_goldmine'
  rm -rf "$tmp_icrf"
