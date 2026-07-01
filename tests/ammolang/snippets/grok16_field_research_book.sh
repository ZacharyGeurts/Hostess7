#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${sg}/Grok16/data/g16-field-research-book.json" ]]
  [[ -f "${sg}/Grok16/lib/field-research-book.py" ]]
  grep -q 'field-research-book/v1' "${sg}/Grok16/data/g16-field-research-book.json"
  grep -q 'field_research_book' "${sg}/Grok16/data/grok16-single-fabric-doctrine.json"
  grep -q 'sync_field_research_book' "${sg}/Grok16/scripts/grok16-integrate.sh"
  GROK16_SG_ROOT="$sg" SG_ROOT="$sg" python3 "${sg}/Grok16/lib/field-research-book.py" verify | grep -q '"ok": true'
  GROK16_SG_ROOT="$sg" SG_ROOT="$sg" python3 "${sg}/Grok16/lib/field-research-book.py" publish | grep -q '"ok": true'
  [[ -f "${sg}/Grok16/data/g16-field-research-book-panel.json" ]]
  [[ -f "${sg}/Grok16/docs/field-research.html" ]]
  grep -q 'field-research.html' "${sg}/Grok16/docs/build-manual.py"
