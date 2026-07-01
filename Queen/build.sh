#!/bin/bash
# Queen Forge entry — RTX exe (replaces legacy shell build).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-${ROOT}}"
export QUEEN_ROOT="${ROOT}"
exec "${ROOT}/scripts/queen-py" "${ROOT}/lib/queen-forge.py" run rtx