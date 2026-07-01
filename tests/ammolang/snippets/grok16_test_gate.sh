#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -x "${sg}/Grok16/scripts/grok16-test-gate.sh" ]]
  [[ -x "${sg}/Grok16/scripts/g16-run-monitored.sh" ]]
  [[ -f "${sg}/Grok16/lib/g16_self_monitor.py" ]]
  grep -q '4.2.0' "${sg}/Grok16/data/grok16-version.json"
  grep -q 'line_safety' "${sg}/Grok16/data/grok16-version.json"
  grep -q 'self_monitor' "${sg}/Grok16/data/grok16-version.json"
  grep -q 'grok16-field-exec-full-bench/v5' "${sg}/Grok16/data/grok16-speed-bench-version.json"
    [[ -f "${sg}/Grok16/data/grok16-version.json" ]]
    SG_ROOT="$sg" GROK16_ROOT="${sg}/Grok16" python3 "${sg}/Grok16/tests/test_g16_self_monitor.py"
    SG_ROOT="$sg" GROK16_ROOT="${sg}/Grok16" python3 "${sg}/Grok16/lib/field_combinatorics.py" fast >/dev/null
    exit 0
  SG_ROOT="$sg" NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$(mktemp -d)" \
    bash "${sg}/Grok16/scripts/grok16-test-gate.sh" smoke
