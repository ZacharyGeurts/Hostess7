#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  nexus_firewall_trust_init
  nexus_firewall_authorize_ip "203.0.113.50" out "test-peer" "run-tests"
  nexus_firewall_is_trusted "203.0.113.50" out
