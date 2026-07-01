#!/usr/bin/env bash
# Local sanctuary — ensure NEXUS panel :9477 before program launch.
set -euo pipefail
export AML_BUILD=0

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
export SG_ROOT="${SG_ROOT:-$(dirname "$ROOT")}"

exec bash "$ROOT/GrokLab/deploy/world-node-panel-ensure.sh"