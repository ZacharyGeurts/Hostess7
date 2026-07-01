#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  nexus_vigil_init
  : >"$NEXUS_VIGIL_ALERTS"
  nexus_vigil_write_state calm 0
  [[ "$(nexus_vigil_get_mode)" == "calm" ]]
