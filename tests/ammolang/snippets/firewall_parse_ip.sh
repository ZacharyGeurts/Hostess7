#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  ip="$(nexus_firewall_parse_ip 'dst=203.0.113.9:4444 proc=evil' dst)"
  [[ "$ip" == "203.0.113.9" ]]
