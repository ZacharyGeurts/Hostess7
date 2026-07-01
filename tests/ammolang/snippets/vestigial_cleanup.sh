#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/nexus-vestigial-cleanup.py" ]]
  [[ -f "${ROOT}/lib/nexus-vestigial-cleanup.sh" ]]
  grep -q 'nexus_vestigial_cleanup_run' "${ROOT}/lib/nexus-vestigial-cleanup.sh"
  grep -q 'nexus_boot_impl_vestigial_cleanup' "${ROOT}/lib/nexus-boot-impl.sh"
  grep -q 'nexus_vestigial_cleanup_run' "${ROOT}/nexus.sh"
  grep -q 'nexus_znetwork_startup_with_us' "${ROOT}/lib/znetwork-field.sh"
  grep -q 'Bypassed OS Networking' "${ROOT}/lib/panel-tray.py"
  grep -q 'Bypassed OS Networking' "${ROOT}/lib/panel-tray.sh"
  grep -q 'nexus-shield.desktop' "${ROOT}/lib/nexus-vestigial-cleanup.py"
  grep -q 'ammocode-stack.desktop' "${ROOT}/lib/nexus-vestigial-cleanup.py"
  grep -q 'never_harm_os' "${ROOT}/lib/nexus-vestigial-cleanup.py"
  tmp_state="$(mktemp -d)"
out=$("$PY" "${ROOT}/lib/nexus-vestigial-cleanup.py" json 2>/dev/null || true); grep -q 'nexus-vestigial-cleanup/v1'
  rm -rf "$tmp_state"
