#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
out=$(NEXUS_STATE_DIR="$NEXUS_STATE_DIR" "$PY" "${ROOT}/lib/connection-gatekeeper.py" --stdin <<'EOF' 2>/dev/null || true); grep -q '"suggestion"'
tcp ESTAB 0 0 10.0.0.5:44444 104.18.29.234:443 users:(("firefox",pid=1,fd=3))
EOF
