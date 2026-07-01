#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/data/field-field-surfaces-doctrine.json" ]]
  grep -q 'c2_taskbar' "${ROOT}/lib/field-plate-meld.py"
  grep -q 'shell_dock' "${ROOT}/lib/field-plate-meld.py"
  grep -q 'field_popcorn' "${ROOT}/lib/field-plate-meld.py"
  grep -q 'field_g16_launch' "${ROOT}/lib/field-plate-meld.py"
  grep -q 'field_gpu' "${ROOT}/lib/field-plate-meld.py"
  grep -q 'field_audio' "${ROOT}/lib/field-plate-meld.py"
  grep -q 'field_broadcaster' "${ROOT}/lib/field-plate-meld.py"
  grep -q '_refresh_shell_dock' "${ROOT}/lib/field-plate-meld.py"
  grep -q 'field_surface_slices' "${ROOT}/lib/field-plate-combinatorics-bridge.py"
  grep -q 'field_surfaces' "${ROOT}/lib/field-plate-combinatorics-bridge.py"
  grep -q 'field_shell_dock' "${ROOT}/lib/field-panel-parallel.py"
  grep -q 'field_popcorn' "${ROOT}/lib/field-panel-parallel.py"
  grep -q 'field_g16_launch' "${ROOT}/lib/field-panel-parallel.py"
  grep -q 'field_audio' "${ROOT}/lib/field-panel-parallel.py"
  grep -q 'field_lock' "${ROOT}/lib/field-panel-parallel.py"
  grep -q 'c2_taskbar' "${ROOT}/lib/field-panel-parallel.py"
  grep -q 'operator_surfaces' "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/lib/field_combinatorics.py"
  grep -q 'c2_taskbar' "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/lib/field_combinatorics.py"
  grep -q 'field_surfaces' "${ROOT}/lib/field-combinatorics-comb.py"
  grep -q 'comb-surfaces-grid' "${ROOT}/panel/combinatorics-studio.html"
  tmp_state="$(mktemp -d)"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    aml_py "field-shell-dock.py" json >/dev/null
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" \
    aml_py "field-popcorn-player.py" json >/dev/null
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" \
    aml_py "field-g16-launch.py" json >/dev/null
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" \
    aml_py "field-gpu-control.py" json >/dev/null
out=$("$PY" "${ROOT}/lib/field-audio-settings.py" json 2>/dev/null || true); grep -q 'field-audio-settings/v1'
out=$("$PY" "${ROOT}/lib/field-plate-combinatorics-bridge.py" build 2>/dev/null || true); grep -q 'field-surfaces-slice'
out=$("$PY" "${ROOT}/lib/field-plate-meld.py" fuse 2>/dev/null || true); grep -q 'shell_dock'
