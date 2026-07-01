#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-antenna-orchestrator.py" ]]
  [[ -f "${ROOT}/lib/field-antenna.sh" ]]
  [[ -f "${ROOT}/lib/field-antenna-launcher.sh" ]]
  [[ -f "${ROOT}/scripts/field-antenna-test.sh" ]]
  grep -q 'field_antenna' "${ROOT}/lib/threat-panel.sh"
  grep -q 'nexus_field_antenna_cycle' "${ROOT}/lib/threat-panel.sh"
  grep -q '/api/field-antenna' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'NEXUS_FIELD_ANTENNA' "${ROOT}/config/nexus.conf"
  grep -q 'antenna)' "${ROOT}/bin/nexus"
  grep -q 'field_antenna' "${ROOT}/lib/signals-field.py"
  grep -q 'fcc_laser_part15' "${ROOT}/data/fcc-signal-registry.json"
  grep -q 'kind == "laser"' "${ROOT}/lib/fcc-signal-lookup.py"
out=$("$PY" "${ROOT}/lib/field-antenna-orchestrator.py" build 2>/dev/null || true); grep -q 'field-antenna/v1'
out=$("$PY" "${ROOT}/lib/fcc-signal-lookup.py" lookup laser 0 0 2>/dev/null || true); grep -q 'fcc_laser_part15'
  printf '{"lat":37.7749,"lon":-122.4194,"source":"test"}\n' > "$NEXUS_STATE_DIR/operator-location.json"
  ant_test_out="$(NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
    aml_py "field-antenna-orchestrator.py" test 2>/dev/null || true)"
  [[ "$ant_test_out" == *'field-antenna-test/v1'* ]]
