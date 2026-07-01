#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/host-map-trash.sh" ]]
  grep -q '/api/host-attack/trash' "${ROOT}/lib/threat-panel-http.py"
  grep -q '_load_trashed_ids' "${ROOT}/lib/host-attack-map.py"
  nexus_host_map_trash_add "test-pin-1"
  nexus_host_map_trash_json | grep -q 'test-pin-1'
