#!/bin/bash
# Queen Forge entry — vendor clones.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-${ROOT}}"
exec pythong "${ROOT}/lib/queen-forge.py" run vendors