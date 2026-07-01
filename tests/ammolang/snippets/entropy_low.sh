#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  echo "hello world" >/tmp/nexus-ent-text.txt
  score="$(nexus_entropy_score /tmp/nexus-ent-text.txt)"
  awk -v s="$score" 'BEGIN { exit (s < 5.0) ? 0 : 1 }'
