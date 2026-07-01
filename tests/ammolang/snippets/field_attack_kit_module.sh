#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-attack-kit.sh" ]]
  [[ -f "${ROOT}/lib/field-attack-kit.py" ]]
  grep -q 'attack_kit' "${ROOT}/lib/threat-panel.sh"
  grep -q '/api/attack-kit/disable' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/attack-kit/kill' "${ROOT}/lib/threat-panel-http.py"
  [[ -f "${ROOT}/lib/hostile-ai-destroy.py" ]]
  [[ -f "${ROOT}/data/hostile-ai-threats-seed.json" ]]
  grep -q 'hostile-ai-panel' "${ROOT}/panel/threat-panel.html"
  grep -q 'AI_BEACON_PRECISION' "${ROOT}/lib/threat-vectors.sh"
  grep -q '/api/hostile-ai' "${ROOT}/lib/threat-panel-http.py"
out=$("$PY" "${ROOT}/lib/hostile-ai-destroy.py" panel 2>/dev/null || true); grep -q 'hostile-ai-destroy/v1'
  grep -q '/api/attack-kit/check-online' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/attack-kit/rekill' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/attack-kit/nokill' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'nexus_field_attack_nokill_target' "${ROOT}/lib/field-attack-kit.sh"
  grep -q 'nokill_target' "${ROOT}/lib/field-attack-kit.py"
  grep -q 'field-nokill.tsv' "${ROOT}/lib/field-attack-kit.py"
  grep -q '"nokill"' "${ROOT}/lib/host-attack-map.py"
  grep -q 'nexus_field_attack_kill_target' "${ROOT}/lib/field-attack-kit.sh"
  grep -q 'nexus_field_attack_rekill_target' "${ROOT}/lib/field-attack-kit.sh"
  grep -q 'nexus_target_dossier' "${ROOT}/lib/field-attack-kit.sh"
  grep -q 'kill_target' "${ROOT}/lib/field-attack-kit.py"
  grep -q 'check_online' "${ROOT}/lib/field-attack-kit.py"
  grep -q 'rekill_target' "${ROOT}/lib/field-attack-kit.py"
  grep -q 'auto_rekill_validated' "${ROOT}/lib/field-attack-kit.py"
  grep -q 'nexus_field_attack_autokill' "${ROOT}/lib/field-attack-kit.sh"
  grep -q 'nexus_field_attack_install_autokill' "${ROOT}/lib/field-attack-kit.sh"
  grep -q 'refuse_kill' "${ROOT}/lib/field-attack-kit.py"
  grep -q 'gate_strike' "${ROOT}/lib/field-attack-kit.py"
  grep -q 'trust-strike-engine' "${ROOT}/lib/field-attack-kit.sh"
  grep -q 'nexus_field_attack_publish_deep' "${ROOT}/lib/field-attack-kit.sh"
  grep -q 'nexus_field_attack_rekill_cycle' "${ROOT}/lib/field-attack-kit.sh"
  grep -q 'nexus_field_attack_rekill_cycle' "${ROOT}/lib/threat-panel.sh"
  grep -q 'nexus_field_attack_rekill_cycle' "${ROOT}/lib/kill-detect.sh"
  grep -q 'NEXUS_FIELD_AUTO_REKILL' "${ROOT}/lib/nexus-settings.sh"
  grep -q 'hardware_destroy' "${ROOT}/lib/field-attack-kit.py"
  grep -q 'nexus_hardware_destroy_target' "${ROOT}/lib/field-attack-kit.sh"
  grep -q 'nexus_field_attack_autokill_certain' "${ROOT}/lib/field-attack-kit.sh"
  grep -q 'nexus_field_attack_forever_kill_enforce' "${ROOT}/lib/field-attack-kit.sh"
  grep -q 'autokill_certain' "${ROOT}/lib/field-attack-kit.py"
  grep -q 'forever_kill_enforce' "${ROOT}/lib/field-attack-kit.py"
  ! grep -q 'nexus_field_attack_auto_crush' "${ROOT}/lib/threat-panel.sh"
  grep -q 'killable' "${ROOT}/lib/host-attack-map.py"
  grep -q 'strike_confidence' "${ROOT}/lib/host-attack-map.py"
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
    "$PY" - <<'PY'
import importlib.util
import time
from pathlib import Path
root = Path(__import__("os").environ["NEXUS_INSTALL_ROOT"])
spec = importlib.util.spec_from_file_location("fak", root / "lib" / "field-attack-kit.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod._record_auto_rekill("203.0.113.99")
assert mod._auto_rekill_cooldown_active("203.0.113.99")
mod.AUTO_REKILL_LOG.unlink(missing_ok=True)
empty = mod.auto_rekill_validated()
assert empty.get("rekilled_count") == 0
mod.NOKILL_TSV.write_text("ts\tip\tvector\tseverity\treason\tsource\n2026-01-01T00:00:00Z\t203.0.113.55\tHOSTILE\thigh\ttest\ttest\n", encoding="utf-8")
refused = mod.kill_target("203.0.113.55")
assert refused.get("nokill_refused")
mod.NOKILL_TSV.unlink(missing_ok=True)
PY
  declare -f nexus_field_attack_json >/dev/null 2>&1
