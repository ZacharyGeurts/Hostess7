#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  nexus_predictive_init
  nexus_predictive_record "entropy-oracle"
  grep -q 'score=' "$NEXUS_PREDICTIVE_STATE"
