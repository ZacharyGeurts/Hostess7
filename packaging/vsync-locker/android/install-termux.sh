#!/usr/bin/env bash
# VSYNC-Locker Termux/Android — guard when display stack available
set -euo pipefail
HERE="$(cd "$(dirname "$0")/../.." && pwd)"
PREFIX="${VSYNC_INSTALL_ROOT:-${HOME}/vsync-locker}"
mkdir -p "${PREFIX}/lib" "${PREFIX}/data" "${PREFIX}/panel" "${PREFIX}/.nexus-state"
cp -a "${HERE}/lib/"* "${PREFIX}/lib/"
cp -a "${HERE}/data/"* "${PREFIX}/data/"
cp -a "${HERE}/panel/"* "${PREFIX}/panel/"
chmod +x "${PREFIX}/lib/"*.sh 2>/dev/null || true
export NEXUS_INSTALL_ROOT="${PREFIX}" NEXUS_STATE_DIR="${PREFIX}/.nexus-state"
python "${PREFIX}/lib/field-vsync-locker.py" harden
python "${PREFIX}/lib/field-vsync-locker.py" launch || true
echo "[vsync-locker] Termux install at ${PREFIX}"