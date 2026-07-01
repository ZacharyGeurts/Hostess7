#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  parsed="$(nexus_packet_parse_ss_line "tcp LISTEN 0 128 0.0.0.0:8080 0.0.0.0:* users:((\"pythong\",pid=99,fd=3))")"
  [[ "$parsed" == *"LISTEN"* && "$parsed" == *"8080"* ]]
  parsed="$(nexus_packet_parse_ss_line "tcp ESTAB 0 0 192.168.1.5:54321 104.18.29.234:443 users:((\"firefox\",pid=1,fd=3))")"
  [[ "$parsed" == *"ESTAB"* && "$parsed" == *"104.18.29.234"* ]]
