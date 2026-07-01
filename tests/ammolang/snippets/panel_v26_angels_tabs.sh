#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  grep -q 'view-dossier' "${ROOT}/panel/threat-panel.html"
  grep -q 'view-research' "${ROOT}/panel/threat-panel.html"
  grep -q 'renderDossiers' "${ROOT}/panel/threat-panel.html"
  grep -q 'Let'\''s Be Angels' "${ROOT}/panel/threat-panel.html"
  grep -q 'angel_dossiers' "${ROOT}/lib/threat-panel.sh"
