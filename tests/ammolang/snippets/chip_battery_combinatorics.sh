#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-chip-battery.py" ]]
  [[ -f "${ROOT}/data/field-chip-battery-seed.json" ]]
  [[ -f "${ROOT}/data/field-chip-battery-doctrine.json" ]]
  grep -q 'ironclad_chips' "${ROOT}/lib/field-panel-parallel.py"
  grep -q 'ironclad_chips' "${ROOT}/lib/field-plate-meld.py"
  grep -q 'ironclad_chips' "${sg}/Grok16/data/g16-field-combinatorics-doctrine.json"
  grep -q 'ironclad_chips' "${sg}/Grok16/lib/field_combinatorics.py"
  grep -q 'ironclad_chips_total' "${ROOT}/lib/field-combinatorics-comb.py"
  [[ -f "${ROOT}/lib/field-ironclad-chips-combinatorics.py" ]]
  [[ -f "${ROOT}/data/field-ironclad-chips-combinatorics-doctrine.json" ]]
  grep -q '/api/chip-battery' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/chips/combinatronic' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'combinatronic' "${ROOT}/data/field-chip-battery-doctrine.json"
  grep -q 'combinatronic_panel' "${ROOT}/lib/field-chip-battery.py"
  grep -q '/api/chips/combinatronic' "${ROOT}/Queen/lib/queen-world.py"
  grep -q 'combinatronic_status' "${ROOT}/Queen/lib/queen-chips.py"
  [[ -f "${ROOT}/Queen/world/queen-chips-cores.css" ]]
  grep -q 'combinatronic' "${ROOT}/Queen/world/queen-chips-cores.js"
  [[ -f "${ROOT}/Queen/world/queen-styles.js" ]]
  [[ -f "${ROOT}/Queen/world/queen-styles.css" ]]
  [[ -f "${ROOT}/Queen/gui/queen-styles-themes.json" ]]
  grep -q 'qb-styles' "${ROOT}/Queen/world/browser.html"
  grep -q 'QueenStyles' "${ROOT}/Queen/world/queen-styles.js"
  [[ -f "${ROOT}/Queen/world/queen-nexus-c2.html" ]]
  [[ -f "${ROOT}/Queen/lib/queen-nexus-c2.py" ]]
  grep -q 'programmatic' "${ROOT}/Queen/data/queen-nexus-c2-panels.json"
  grep -q 'panel_thumbnail' "${ROOT}/Queen/lib/queen-desktop.py"
  grep -q 'programmatic' "${ROOT}/data/field-host-desktop-doctrine.json"
  grep -q 'coco2' "${ROOT}/Queen/data/queen-game-room.json"
  grep -q 'launch_emulator' "${ROOT}/Queen/lib/queen-chips.py"
  grep -q 'emulator_pump_loop' "${ROOT}/Queen/lib/queen-chips.py"
  grep -q 'spawn_rtx' "${ROOT}/Queen/world/queen-game-room.js"
  grep -q 'gr-fb' "${ROOT}/Queen/world/queen-game-room.html"
  grep -q 'pollFramebuffer' "${ROOT}/Queen/world/queen-game-room.js"
  grep -q '_launch_emulator_rom' "${ROOT}/Queen/lib/queen-launch-chamber.py"
  grep -q '_retro_chips_posture' "${ROOT}/lib/field-plate-combinatorics-bridge.py"
  grep -q 'FieldChips' "${ROOT}/lib/field-plate-combinatorics-bridge.py"
  grep -q 'data-rom-path' "${ROOT}/Queen/world/queen-nes-cartridge-theater.js"
  grep -q 'comb-launch-gameroom' "${ROOT}/panel/assets/combinatorics-studio.js"
  grep -q 'queen-sweet-anita-protocol' "${ROOT}/Queen/lib/queen-sweet-anita-protocol.py"
  grep -q 'queen-nes-library' "${ROOT}/Queen/lib/queen-nes-library.py"
  grep -q '/api/nes-library' "${ROOT}/Queen/lib/queen-world.py"
  grep -q '/api/sap' "${ROOT}/Queen/lib/queen-world.py"
  grep -q 'gr-nes-grid' "${ROOT}/Queen/world/queen-game-room.html"
  grep -q 'QueenSAP' "${ROOT}/Queen/world/queen-game-room-sap.js"
  grep -q 'have_first' "${ROOT}/Queen/world/queen-game-room.html"
  grep -q 'gr-layout' "${ROOT}/Queen/world/queen-game-room.html"
  grep -q 'theater_pct' "${ROOT}/Queen/data/queen-game-room.json"
  [[ -f "${ROOT}/Queen/data/queen-test-roms.json" ]]
  grep -q 'resolve_test_rom' "${ROOT}/Queen/lib/queen-chips.py"
  [[ -f "${ROOT}/data/field-chip-path-predict-seed.json" ]]
  grep -q 'code_path_prediction' "${ROOT}/data/field-chip-battery-doctrine.json"
  grep -q 'hard_percentages' "${ROOT}/lib/field-ironclad-chips-combinatorics.py"
  grep -q 'narrow_band' "${sg}/Grok16/data/g16-power-sort-doctrine.json"
  grep -q 'chip_paths' "${sg}/Grok16/lib/field-power-sort.py"
  tmp_state="$(mktemp -d)"
  chip_out="$(mktemp)"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    "$PY" "$ROOT/Queen/lib/queen-chips.py" dispatch <<< '{"action":"launch","system":"nes","spawn_rtx":false}' >"$chip_out" 2>/dev/null
  grep -m1 -q '"mode": "chips"' "$chip_out"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    aml_py "field-chip-battery.py" verify >"$chip_out" 2>/dev/null
  grep -m1 -qF '"ok": true' "$chip_out"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    aml_py "field-chip-battery.py" battery >"$chip_out" 2>/dev/null
  grep -m1 -q 'field-chip-battery/v1' "$chip_out"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    aml_py "field-chip-battery.py" paths >"$chip_out" 2>/dev/null
  grep -m1 -qE '"total_pct": 100(\.0)?' "$chip_out"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    aml_py "field-chip-battery.py" combinatronic >"$chip_out" 2>/dev/null
  grep -m1 -q 'field-chips-combinatronic/v1' "$chip_out"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    "$PY" "$ROOT/Queen/lib/queen-chips.py" combinatronic >"$chip_out" 2>/dev/null
  grep -m1 -q 'field-chips-combinatronic/v1' "$chip_out"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    python3 "$sg/Grok16/lib/field_combinatorics.py" publish >"$chip_out" 2>/dev/null
  grep -m1 -q 'ironclad_chips' "$chip_out"
  rm -f "$chip_out"
  rm -rf "$tmp_state"
