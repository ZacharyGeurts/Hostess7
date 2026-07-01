#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/data/single-field-depth-doctrine.json" ]]
  [[ -f "${ROOT}/lib/field-depth-singularizer.py" ]]
  [[ -f "${ROOT}/lib/field-depth-singularizer.sh" ]]
  [[ -f "${ROOT}/Queen/lib/queen-field-sanity.py" ]]
  [[ -f "${ROOT}/Queen/lib/queen-field-net.py" ]]
  [[ -f "${ROOT}/lib/field-panel-field.py" ]]
  grep -q 'single_field_depth' "${ROOT}/data/ironclad-field-sanity-doctrine.json"
  grep -q 'depth_singularizer' "${ROOT}/data/single-field-depth-doctrine.json"
  grep -q 'depth_field_impossible' "${ROOT}/data/single-field-depth-doctrine.json"
  grep -q 'depth_fields_sealed_and_destroyed' "${ROOT}/data/single-field-depth-doctrine.json"
  grep -q 'sealed and destroyed' "${ROOT}/data/ironclad-meld-extensions.json"
  grep -q 'nexus_depth_singularizer_cycle' "${ROOT}/lib/nexus-daemon.sh"
  grep -q 'max_field_depth": 0' "${ROOT}/Queen/data/queen-field-browser-doctrine.json"
  grep -q 'MAX_DEPTH = 0' "${ROOT}/Queen/world/queen-field-engine.js"
  grep -q 'singularizeDomUrls' "${ROOT}/Queen/world/queen-field-sanity.js"
  grep -q 'snapPitsInstant' "${ROOT}/Queen/world/queen-field-sanity.js"
  grep -q 'snap_dimensional_pits' "${ROOT}/lib/field-depth-singularizer.py"
out=$("$PY" "${ROOT}/lib/field-depth-singularizer.py" instant <<'EOF' 2>/dev/null || true); grep -q '"pits_snapped": 2'
{"layers":[{"id":"pit-a","url":"http://127.0.0.1:9477/field?field_depth=3","depth":3,"active":true},{"id":"pit-b","url":"http://127.0.0.1:9481/world/","depth":2}]}
EOF
out=$("$PY" "${ROOT}/lib/field-depth-singularizer.py" strip-url 'http://127.0.0.1:9477/field?field_depth=3' 2>/dev/null || true); grep -q '"changed": true'
out=$("$PY" "${ROOT}/lib/field-depth-singularizer.py" forbid 'http://127.0.0.1:9477/field?field_depth=3' 2>/dev/null || true); grep -q '"depth_fields_sealed_and_destroyed": true'
out=$("$PY" "${ROOT}/lib/field-depth-singularizer.py" impossibility 2>/dev/null || true); grep -q 'creation_forbidden'
out=$("$PY" "${ROOT}/Queen/lib/queen-field-sanity.py" pass <<'EOF' 2>/dev/null || true); grep -q '"single_field_depth": true'
{"layers":[{"id":"a","url":"http://127.0.0.1:9477/field?field_depth=3","depth":3,"active":true}]}
EOF
  tmp_defrag="$(mktemp -d)"
  printf '%s\n' '{"layers":[{"url":"http://127.0.0.1:9477/field?field_depth=2","depth":2}],"field_depth":3}' \
    > "${tmp_defrag}/ironclad-field-sanity-panel.json"
out=$("$PY" "${ROOT}/lib/field-depth-singularizer.py" cycle 2>/dev/null || true); grep -q '"fixes":'
  ! grep -q 'field_depth=' "${tmp_defrag}/ironclad-field-sanity-panel.json"
  grep -q '"depth": 0' "${tmp_defrag}/ironclad-field-sanity-panel.json"
  rm -rf "$tmp_defrag"
out=$("$PY" "${ROOT}/Queen/lib/queen-field-net.py" json 2>/dev/null 2>/dev/null || true); grep -q 'single_field_depth' || \
    NEXUS_INSTALL_ROOT="$ROOT" "$PY" -c "
import importlib.util
from pathlib import Path
p=Path('${ROOT}/Queen/lib/queen-field-net.py')
spec=importlib.util.spec_from_file_location('qfn', p)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
c=m.classify_url('http://127.0.0.1:9477/field?field_depth=5')
assert c.get('field_depth')==0 and c.get('field_on_field') is False and c.get('depth_field_impossible') is True and c.get('depth_fields_sealed_and_destroyed') is True
print('ok')
"
