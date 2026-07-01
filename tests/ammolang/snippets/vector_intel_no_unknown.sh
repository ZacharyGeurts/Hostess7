#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
gk="${ROOT}/lib/connection-gatekeeper.py"
intel="${ROOT}/lib/vector-intel.py"
  [[ -f "$intel" && -f "$gk" ]]
  ! grep -q 'public_unknown' "$gk"
  grep -q 'classified_remote' "$gk"
  grep -q 'never_unknown' "$intel"
