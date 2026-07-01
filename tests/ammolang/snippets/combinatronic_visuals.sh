#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
[[ -f "${ROOT}/lib/field-combinatronic-visuals.py" ]]
[[ -f "$ROOT/data/field-combinatronic-chip-catalog.json" ]]
[[ -f "$ROOT/data/field-combinatronic-visuals-doctrine.json" ]]
grep -q '/api/combinatronic/visuals' "${ROOT}/lib/threat-panel-http.py"
grep -q '/api/combinatronic/visuals' "$ROOT/Queen/lib/queen-world.py"
grep -q 'inventory' "${ROOT}/lib/field-combinatronic-visuals.py"
grep -q 'build_registry' "${ROOT}/lib/field-combinatronic-visuals.py"
grep -q 'qcc-chip-gallery' "$ROOT/Queen/world/queen-chips-cores.html"
grep -q 'qcc-book-gallery' "$ROOT/Queen/world/queen-chips-cores.js"
[[ -f "$ROOT/data/field-combinatronic-visuals-manifest.json" ]]
[[ -f "$ROOT/data/combinatronic-visuals/chips/cyrix_6x86.png" ]]
[[ -f "$ROOT/data/combinatronic-visuals/books/python.png" ]]
[[ -f "$ROOT/Queen/world/assets/combinatronic/chips/cyrix_6x86.png" ]]
vis_out="$(mktemp)"
if [[ ! -f "$ROOT/library/dewey/000-computer-science/explaining_python/explaining_python.h7c" ]]; then
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$NEXUS_STATE_DIR" \
    aml_py "field-dewey-library.py" migrate >"$vis_out" 2>/dev/null
  grep -m1 -qF '"ok": true' "$vis_out"
fi
NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$NEXUS_STATE_DIR" \
  aml_py "field-combinatronic-visuals.py" manifest >"$vis_out" 2>/dev/null
grep -m1 -qF 'field-combinatronic-visuals' "$vis_out"
NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$NEXUS_STATE_DIR" \
  aml_py "field-combinatronic-visuals.py" chip mame_m6502 >"$vis_out" 2>/dev/null
grep -m1 -qF '"pins": 40' "$vis_out"
NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$NEXUS_STATE_DIR" \
  aml_py "field-combinatronic-visuals.py" book qbasic >"$vis_out" 2>/dev/null
grep -m1 -qF 'explaining_qbasic' "$vis_out"
NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$NEXUS_STATE_DIR" \
  aml_py "field-combinatronic-visuals.py" registry >"$vis_out" 2>/dev/null
grep -m1 -qF 'field-combinatronic-visuals-registry/v1' "$vis_out"
NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$NEXUS_STATE_DIR" \
  aml_py "field-combinatronic-visuals.py" repair >"$vis_out" 2>/dev/null
grep -m1 -qF '"ok": true' "$vis_out"
NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$NEXUS_STATE_DIR" AML_INLINE=1 \
  aml_py "field-combinatronic-visuals.py" verify >"$vis_out" 2>/dev/null
grep -m1 -qF '"ok": true' "$vis_out"
NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$NEXUS_STATE_DIR" \
  aml_py "field-combinatronic-visuals.py" pattern chip_png >"$vis_out" 2>/dev/null
grep -m1 -qF '"pattern_id": "chip_png"' "$vis_out"
rm -f "$ROOT/data/combinatronic-visuals/chips/mame_m6502.png"
NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$NEXUS_STATE_DIR" \
  aml_py "field-combinatronic-visuals.py" repair >"$vis_out" 2>/dev/null
grep -m1 -qF '"ok": true' "$vis_out"
rm -f "$vis_out"
[[ -f "$ROOT/data/combinatronic-visuals/chips/mame_m6502.png" ]]
[[ -f "$ROOT/data/field-combinatronic-visuals-registry.json" ]]
