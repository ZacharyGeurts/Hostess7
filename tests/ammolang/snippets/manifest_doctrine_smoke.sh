#!/usr/bin/env bash
set -euo pipefail
ROOT="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
cd "$ROOT"
test -f MANIFEST.sha256
awk 'NF>=2 {n++} END{exit (n>0)?0:1}' MANIFEST.sha256
python3 -c "import json; json.load(open('data/field-chips-core-doctrine.json'))"
grep -q '3\.1\.0-beta' VERSION.md || grep -q 'VERSION.md' README.md
echo "manifest_doctrine_smoke=ok"