#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
[[ -f "${ROOT}/lib/field-g16-script-compile.py" ]]
[[ -f "${ROOT}/data/field-g16-script-compile-doctrine.json" ]]
grep -q 'hot_scripts' "${ROOT}/data/field-g16-script-compile-doctrine.json"
grep -q 'field-g16-script-compile' "${ROOT}/lib/nexus-g16-recompile.py"
grep -q 'resolve_argv' "${ROOT}/lib/field-ammolang-test.py"
[[ -f "${sg}/Grok16/bin/g16" ]]
out=$("$PY" "${ROOT}/lib/field-g16-script-compile.py" compile "${ROOT}/lib/field-combinatronic-balance.py" 2>/dev/null || true)
grep -q 'field-g16-script-compile/v1' <<<"$out"
grep -q '"ok": true' <<<"$out"
bin="${ROOT}/lib/bin/field-combinatronic-balance"
[[ -x "$bin" ]]
"$bin" json 2>/dev/null | grep -q 'field-combinatronic-balance'
