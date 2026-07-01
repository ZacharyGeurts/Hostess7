#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  grep -q 'data-block-day' "${ROOT}/panel/threat-panel.html"
  grep -q 'data-block-forever' "${ROOT}/panel/threat-panel.html"
  grep -q 'data-unblock-day' "${ROOT}/panel/threat-panel.html"
  grep -q 'Trust forever' "${ROOT}/panel/threat-panel.html"
  grep -q 'Permitted — zero-cost fast path' "${ROOT}/panel/threat-panel.html"
