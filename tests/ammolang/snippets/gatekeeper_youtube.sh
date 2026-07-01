#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
out=$(NEXUS_STATE_DIR="$NEXUS_STATE_DIR" "$PY" "${ROOT}/lib/connection-gatekeeper.py" --stdin <<'EOF' 2>/dev/null || true); grep -q E '"verdict":\s*"USER_OK"'
tcp ESTAB 0 0 10.0.0.5:52444 172.217.14.206:443 users:(("firefox",pid=1,fd=3))
EOF
out=$(NEXUS_STATE_DIR="$NEXUS_STATE_DIR" "$PY" "${ROOT}/lib/connection-gatekeeper.py" --stdin <<'EOF' 2>/dev/null || true); grep -q '"human_touch": "music"'
tcp ESTAB 0 0 10.0.0.5:52444 172.217.14.206:443 users:(("firefox",pid=1,fd=3))
EOF
