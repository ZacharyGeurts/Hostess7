#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-non-fielded-safety.py" ]]
  grep -q 'NEXUS_FIELD_PUBLISH_REQUIRES_DEFIELD' "${ROOT}/config/nexus.conf"
  grep -q 'NEXUS_FIELD_DRIVE_STATE_REDIRECT=0' "${ROOT}/config/nexus.conf"
  grep -q 'non_fielded_safety' "${ROOT}/data/field-underlay-switch-doctrine.json"
  grep -q 'non_fielded_safety' "${ROOT}/data/field-switch-safety-doctrine.json"
  grep -q 'defield_audit' "${ROOT}/lib/field-drive-converter.py"
  grep -q 'field_one' "${ROOT}/data/field-one-doctrine.json"
out=$("$PY" "${ROOT}/lib/field-one.py" json 2>/dev/null 2>/dev/null || true); grep -q '"field_one": true'
  grep -q 'hostile_scan' "${ROOT}/data/field-one-doctrine.json"
  grep -q 'FIELD_NOT_ONE' "${ROOT}/lib/field-one-hostile-scan.py"
out=$("$PY" "${ROOT}/lib/field-one-hostile-scan.py" --dry-run 2>/dev/null 2>/dev/null || true); grep -q '"field_one": "field_one"'
  grep -q 'purge_nested_drive_field' "${ROOT}/lib/field-non-fielded-safety.py"
  grep -q '_gate_publish' "${ROOT}/lib/field-drive-system.py"
  grep -q 'nexus-field' "${ROOT}/World_Redata/redata/safety.py" 2>/dev/null \
    || grep -q 'nexus-field' "${ROOT}/../World_Redata/redata/safety.py"
  grep -q '_non_fielded_posture' "${ROOT}/lib/field-underlay-switch.py"
  grep -q 'defield-audit' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'purge-nested-drive' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'ti-defield-status' "${ROOT}/panel/assets/tristate-installer.js"
  grep -q 'f9-defield-audit' "${ROOT}/panel/assets/underlay-f9.js"
  grep -q 'NEXUS_FIELD_DRIVE_STATE_REDIRECT' "${ROOT}/lib/field-drive-system.sh"
  tmp_state="$(mktemp -d)"
  tmp_team="$(mktemp -d)"
  mkdir -p "${tmp_team}/nexus-field/system"
  echo probe >"${tmp_team}/nexus-field/system/hotspot.txt"
out=$("$PY" "${ROOT}/lib/field-non-fielded-safety.py" audit 2>/dev/null 2>/dev/null || true); grep -q 'nested_nexus_field_on_drives'
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$(dirname "$ROOT")" \
out=$("$PY" "${ROOT}/lib/field-non-fielded-safety.py" gate-publish 2>/dev/null 2>/dev/null || true); grep -q 'nested_field_on_drive'
out=$("$PY" "${ROOT}/lib/field-drive-system.py" json 2>/dev/null 2>/dev/null || true); grep -q 'host_mirror_only'
  rm -rf "$tmp_state" "$tmp_team"
