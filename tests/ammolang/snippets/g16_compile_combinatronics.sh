#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  queen="${ROOT}/Queen"
  [[ -f "${sg}/Grok16/lib/g16-compile-combinatronics.py" ]]
  [[ -f "${sg}/Grok16/data/g16-compile-combinatronics-doctrine.json" ]]
  [[ -f "${sg}/Grok16/tests/test_g16_compile_combinatronics.py" ]]
  grep -q 'compile_gate' "${sg}/Grok16/scripts/grok16-ai-compile.py"
  grep -q '_compile_combinatronics_mod' "${queen}/lib/queen-launch-singular-field.py"
  grep -q '_ideal_compile_profile' "${sg}/Grok16/scripts/grok16-profile-flags.py"
  grep -q 'g16-compile-combinatronics.py' "${sg}/Grok16/scripts/grok16-toolchain.sh"
  grep -q 'compiled_creation' "${sg}/Grok16/data/g16-field-combinatorics-doctrine.json"
  grep -q 'combinatronics' "${sg}/Grok16/data/field-exec-uncompiled-doctrine.json"
  gate_out="$(mktemp)"
  "$PY" "${sg}/Grok16/lib/g16-compile-combinatronics.py" gate >"$gate_out" 2>/dev/null || true
  grep -q 'g16-compile-combinatronics/v1' "$gate_out"
  rm -f "$gate_out"
    GROK16_ROOT="${sg}/Grok16" SG_ROOT="${sg}" NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}" \
      "$PY" "${sg}/Grok16/tests/test_g16_compile_combinatronics.py"
