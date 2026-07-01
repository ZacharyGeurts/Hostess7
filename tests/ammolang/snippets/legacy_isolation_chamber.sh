#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-legacy-isolation-chamber.py" ]]
  [[ -f "${ROOT}/data/field-legacy-isolation-chamber-doctrine.json" ]]
  grep -q 'legacy_isolation_chamber' "${ROOT}/data/field-plate-test-registry.json"
  grep -q 'gcc-14' "${ROOT}/data/field-legacy-isolation-chamber-doctrine.json"
  grep -q '"basic"' "${ROOT}/data/field-legacy-isolation-chamber-doctrine.json"
  grep -q '"qbasic"' "${ROOT}/data/field-legacy-isolation-chamber-doctrine.json"
  grep -q '"freebasic"' "${ROOT}/data/field-legacy-isolation-chamber-doctrine.json"
  tmp_state="$(mktemp -d)"
out=$("$PY" "${ROOT}/lib/field-legacy-isolation-chamber.py" probe 2>/dev/null || true); grep -q 'field-legacy-isolation-toolchains'
out=$("$PY" "${ROOT}/lib/field-legacy-isolation-chamber.py" refresh 2>/dev/null || true); grep -q '"action": "refresh_toolchains"'
out=$("$PY" "${ROOT}/lib/field-legacy-isolation-chamber.py" chamber --lang qbasic 2>/dev/null || true); grep -q '"ok": true'
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    aml_py "field-legacy-isolation-chamber.py" verify > /tmp/legacy-chamber-verify.json
  python3 -c "import json; d=json.load(open('/tmp/legacy-chamber-verify.json')); assert d.get('ok'), d; assert d['chamber']['passed']>=8, d['chamber']"
  rm -rf "$tmp_state"
