#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  python3 "${sg}/Grok16/tests/test_g16_self_monitor.py" | grep -q 'PASS'
  grep -q '"metrics"' "${sg}/Grok16/data/grok16-speed-bench-version.json"
