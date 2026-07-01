#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  nexus_threat_vector_init
  nexus_threat_record "PACKET_INJECTION" high "test=injection"
  nexus_threat_panel_publish
  "$PY" -c "
import json, sys
d = json.load(open(sys.argv[1], encoding='utf-8'))
assert any(t.get('vector') == 'PACKET_INJECTION' for t in d.get('threats') or [])
" "$NEXUS_STATE_DIR/threat-panel.json"
