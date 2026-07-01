#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  queen="${ROOT}/Queen"
  [[ -f "${ROOT}/lib/nexus-g16-recompile.py" ]]
  [[ -f "${ROOT}/data/nexus-g16-integrate-doctrine.json" ]]
  [[ -f "${ROOT}/scripts/nexus-g16-recompile.sh" ]]
  grep -q '_combinatronics_profile' "${ROOT}/lib/nexus-g16-bridge.py"
  grep -q 'balance_combinatronics' "${ROOT}/lib/nexus-g16-recompile.py"
  grep -q 'integrate' "${ROOT}/scripts/sync-field-stack.sh"
  grep -q '_g16_combinatronics_gate' "${queen}/scripts/g16-build.sh"
  grep -q '_combinatronics_compile_gate' "${queen}/lib/forge/tools.py"
  grep -q 'g16-compile-combinatronics.py' "${ROOT}/lib/field-outside-asm.sh"
  grep -q 'integrate' "${ROOT}/data/nexus-g16-compile-doctrine.json"
  bal_out="$(mktemp)"
  aml_py "nexus-g16-recompile.py" balance >"$bal_out" 2>/dev/null || true
  grep -q 'nexus-g16-recompile-balance/v1' "$bal_out"
  rm -f "$bal_out"
