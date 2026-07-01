#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-plate-meld-orchestrator.py" ]]
  grep -q '/api/plate-meld-orchestrator' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'plate_meld_orchestrator' "${ROOT}/lib/field-panel-parallel.py"
  grep -q 'audit_connectivity' "${ROOT}/lib/field-plate-meld-orchestrator.py"
  grep -q 'bottom_cpu_posture' "${ROOT}/lib/field-plate-meld-orchestrator.py"
  grep -q 'build_connection_graph' "${ROOT}/lib/field-plate-meld-orchestrator.py"
  tmp_state="$(mktemp -d)"
  run_orch() {
    NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
      AML_INLINE="${AML_INLINE:-0}" AML_TEST_DIRECT="${AML_TEST_DIRECT:-0}" \
      aml_py "field-plate-meld-orchestrator.py" "$@"
  }
  out=$(run_orch audit 2>/dev/null || true)
  grep -q 'field-plate-meld-connectivity-audit' <<<"$out"
  out=$(run_orch connect 2>/dev/null || true)
  grep -q 'field-plate-meld-connection-graph' <<<"$out"
  out=$(run_orch bottom 2>/dev/null || true)
  grep -q 'field-plate-meld-bottom-cpu' <<<"$out"
  rm -rf "$tmp_state"
