#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  tmp_state="$(mktemp -d)"
  grep -q 'retaliate_threat' "${sg}/Grok16/lib/field_combinatorics.py"
  grep -q 'record_rejection' "${sg}/Grok16/lib/field_combinatorics.py"
  grep -q 'reject_retaliate' "${sg}/Grok16/data/g16-field-combinatorics-doctrine.json"
  grep -q 'combinatorics_threat_retaliate' "${ROOT}/data/field-diagnostic-mode-doctrine.json"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" GROK16_ROOT="$sg/Grok16" SG_ROOT="$sg" \
    python3 "$sg/Grok16/lib/field_truth_blocks.py" publish >/dev/null
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" GROK16_ROOT="$sg/Grok16" SG_ROOT="$sg" \
    python3 "$sg/Grok16/lib/field_combinatorics.py" rebuild >/dev/null
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" GROK16_ROOT="$sg/Grok16" SG_ROOT="$sg" \
    python3 -c "
import json
from pathlib import Path
state = Path('${tmp_state}')
panel_path = state / 'g16-field-combinatorics-panel.json'
panel = json.loads(panel_path.read_text())
panel.setdefault('hard_limits', {})['tampered'] = True
panel_path.write_text(json.dumps(panel, indent=2) + '\n')
print('tampered')
" | grep -q 'tampered'
  comb_out="$(mktemp)"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" GROK16_ROOT="$sg/Grok16" SG_ROOT="$sg" \
    aml_py "field-plate-combinatorics-bridge.py" build >"$comb_out" 2>/dev/null
  grep -m1 -qF '"ok": true' "$comb_out"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" GROK16_ROOT="$sg/Grok16" SG_ROOT="$sg" \
    aml_py "field-plate-combinatorics-bridge.py" build >"$comb_out" 2>/dev/null
  grep -m1 -q 'combinatorics_rejected' "$comb_out"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" GROK16_ROOT="$sg/Grok16" SG_ROOT="$sg" \
    python3 "$sg/Grok16/lib/field_combinatorics.py" fast >"$comb_out" 2>/dev/null
  grep -m1 -q '"rejected": true' "$comb_out"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" GROK16_ROOT="$sg/Grok16" SG_ROOT="$sg" \
    python3 "$sg/Grok16/lib/field_combinatorics.py" threat >"$comb_out" 2>/dev/null
  grep -m1 -q 'field-combinatorics-threat' "$comb_out"
  [[ -f "${tmp_state}/field-combinatorics-reject-ledger.jsonl" ]]
  mkdir -p "${tmp_state}"
  echo '{"role":"operator","ts":"2099-01-01T00:00:00Z","text":"active"}' > "${tmp_state}/hostess7-command.jsonl"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" GROK16_ROOT="$sg/Grok16" SG_ROOT="$sg" \
    python3 "$sg/Grok16/lib/field_combinatorics.py" fast >"$comb_out" 2>/dev/null
  grep -m1 -q '"deferred": true' "$comb_out"
  rm -f "$comb_out"
  rm -rf "$tmp_state"
