#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  grep -q 'axis-grid-prominent' "${ROOT}/panel/threat-panel.html"
  grep -q 'renderSuggestionBox(sug, v, c.scores)' "${ROOT}/panel/threat-panel.html"
  grep -q 'renderAxisBars(scores)' "${ROOT}/panel/threat-panel.html"
  ! grep -q 'score-meters' "${ROOT}/panel/threat-panel.html"
