#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/data/human-dossier-kill-orders.json" ]]
  [[ -f "${ROOT}/lib/human-dossier.sh" ]]
  grep -q 'human_dossier' "${ROOT}/lib/threat-panel.sh"
  grep -q 'view-human-dossier' "${ROOT}/panel/threat-panel.html"
  grep -q 'renderHumanDossiers' "${ROOT}/panel/threat-panel.html"
  grep -q 'nexus_human_dossier_json' "${ROOT}/lib/human-dossier.sh"
  "$PY" -c "import json; d=json.load(open('${ROOT}/data/human-dossier-kill-orders.json')); assert len(d['ips'])>=24; assert d['analyst']=='Grok Heavy'"
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
    bash -c "source '${ROOT}/lib/human-dossier.sh' && nexus_human_dossier_sync && nexus_human_dossier_json" | grep -q '147.93.191.75'
