#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  nexus_sign_manifest "$NEXUS_STATE_DIR/test.manifest"
  NEXUS_MANIFEST="$NEXUS_STATE_DIR/test.manifest"
  nexus_verify_integrity
