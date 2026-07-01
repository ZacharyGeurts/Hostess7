#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  NEXUS_MANIFEST="$NEXUS_STATE_DIR/test.manifest"
  nexus_sign_manifest "$NEXUS_MANIFEST"
  nexus_seal_refresh
  nexus_seal_verify
