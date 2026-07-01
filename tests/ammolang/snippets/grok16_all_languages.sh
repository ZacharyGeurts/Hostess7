#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${sg}/Grok16/scripts/sync-all-languages.py" ]]
  [[ -f "${sg}/Grok16/data/grok16-languages.json" ]]
  grep -q '"launch_packaging": true' "${sg}/Grok16/data/grok16-languages.json"
  grep -q '"uncompiled_default": true' "${sg}/Grok16/data/grok16-languages.json"
  grep -q '"javascript"' "${sg}/Grok16/data/grok16-languages.json"
  grep -q '"haskell"' "${sg}/Grok16/data/grok16-languages.json"
  grep -q '"g16-interp"' "${sg}/Grok16/forge/language_tools.py"
  grep -q 'g16_ext_lang' "${sg}/Grok16/driver/g16-unified.c"
  grep -q 'python_speedups' "${sg}/Grok16/data/field-exec-uncompiled-doctrine.json"
  [[ -f "${sg}/Grok16/examples/languages/python/python.launch" ]]
  [[ -f "${sg}/Grok16/examples/languages/javascript/javascript.launch" ]]
  grep -q '"compile": false' "${sg}/Grok16/examples/languages/python/python.launch"
  out="$(mktemp)"
  SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" "$PY" "${sg}/Grok16/scripts/sync-all-languages.py" >"$out" 2>/dev/null || true
  grep -qE '"languages": [0-9]+' "$out"
  python3 -c "import json,sys; d=json.load(open('$out')); assert d.get('ok') and int(d.get('languages',0))>=55, d"
  aml_py "field-program-combinatronic.py" build >"$out" 2>/dev/null || true
  grep -q 'field-program-combinatronic-panel' "$out"
  aml_py "g16-combinatronic-rebalance.py" rebalance --force >"$out" 2>/dev/null || true
  grep -q '"action": "rebalance"' "$out"
  aml_py "field-g16-launch.py" discover >"$out" 2>/dev/null || true
  grep -q 'languages/' "$out"
  rm -f "$out"
