#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/znetwork-startup-retire.py" ]]
  grep -q 'startup_retire' "${ROOT}/data/znetwork-doctrine.json"
  grep -q 'nexus_znetwork_startup_retire_host' "${ROOT}/lib/znetwork-field.sh"
  grep -q 'startup_retire_host' "${ROOT}/data/znetwork-doctrine.json"
  grep -q 'disable_startup_only_no_live_stop' "${ROOT}/data/znetwork-doctrine.json"
  grep -q 'nexus_install_reboot_prompt' "${ROOT}/lib/installer.sh"
  grep -q 'nexus_install_reboot_prompt' "${ROOT}/lib/nxf-install.sh"
  tmp_state="$(mktemp -d)"
out=$("$PY" "${ROOT}/lib/znetwork-startup-retire.py" detect 2>/dev/null || true); grep -q '"schema": "znetwork-startup-retire/v1"'
  printf 'running=1\n' >"${tmp_state}/znetwork-running.marker"
  printf '{"schema":"znetwork-relayer/v1","active":true}\n' >"${tmp_state}/znetwork-relayer.json"
out=$("$PY" "${ROOT}/lib/znetwork-startup-retire.py" takeover 2>/dev/null || true); grep -q '"ok": true'
  rm -rf "$tmp_state"
