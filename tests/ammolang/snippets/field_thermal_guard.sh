#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-thermal-guard.py" ]]
  [[ -f "${ROOT}/lib/field-global-redata.py" ]]
  [[ -f "${ROOT}/data/field-thermal-guard-doctrine.json" ]]
  grep -q 'NEXUS_FIELD_THERMAL_GUARD' "${ROOT}/config/nexus.conf"
  grep -q 'NEXUS_FIELD_MAX_JOULES_PER_SEC' "${ROOT}/config/nexus.conf"
  grep -q 'NEXUS_FIELD_REDATA_CHUNK' "${ROOT}/config/nexus.conf"
  grep -q 'nexus_boot_impl_thermal_guard_init' "${ROOT}/lib/nexus-boot-impl.sh"
  grep -q 'nexus_boot_impl_bounded_redata' "${ROOT}/lib/nexus-boot-impl.sh"
  grep -q 'field-thermal-guard' "${ROOT}/lib/nexus-daemon.sh"
  grep -q 'safe_global_redata' "${ROOT}/lib/field-thermal-guard.py"
  grep -q 'headroom_pct' "${ROOT}/lib/field-thermal-guard.py"
  grep -q 'gatekeeper_tighten' "${ROOT}/lib/field-thermal-guard.py"
  grep -q '_field_thermal_meta' "${ROOT}/lib/connection-gatekeeper.py"
  grep -q 'field_thermal_guard' "${ROOT}/lib/field-panel-parallel.py"
  grep -q 'monolithic_blast' "${ROOT}/lib/field-global-redata.py"
  tmp_state="$(mktemp -d)"
out=$("$PY" "${ROOT}/lib/field-thermal-guard.py" json 2>/dev/null 2>/dev/null || true); grep -q 'headroom_pct'
out=$("$PY" "${ROOT}/lib/field-global-redata.py" boot-test 2>/dev/null 2>/dev/null || true); grep -q 'incremental'
out=$("$PY" "${ROOT}/lib/field-global-redata.py" boot-test 2>/dev/null 2>/dev/null || true); grep -q 'monolithic_blast'
  rm -rf "$tmp_state"
