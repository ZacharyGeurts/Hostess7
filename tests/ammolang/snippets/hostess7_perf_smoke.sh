#!/usr/bin/env bash
# Hostess7 3.1.0-beta — perf profile + error dashboard smoke (no live boot required)
set -euo pipefail
ROOT="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state-test-isolated}"
mkdir -p "$NEXUS_STATE_DIR"

python3 "$ROOT/lib/field-performance-flyout.py" json | grep -q 'field-performance-flyout/v1'
python3 "$ROOT/lib/field-central-log.py" panel | grep -q 'hostess7-central-log-panel/v1'
python3 "$ROOT/lib/hostess7-runtime-mode.py" lite status | grep -q 'hostess7-lite-mode/v1'
python3 "$ROOT/lib/field-error-dashboard.py" json | grep -q 'field-error-dashboard/v1'
python3 -c "import json; json.load(open('$ROOT/data/hostess7-boot-timeouts.json'))"
python3 -c "import json; json.load(open('$ROOT/data/hostess7-lite-mode-doctrine.json'))"
grep -q 'field-error-dashboard' "$ROOT/lib/threat-panel-http.py"
grep -q 'profile|perf-profile' "$ROOT/Hostess7/Hostess7.sh"
echo "hostess7_perf_smoke=ok"