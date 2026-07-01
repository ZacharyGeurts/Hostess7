#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")/../.." && pwd)"
PREFIX="${VSYNC_INSTALL_ROOT:-/usr/local/vsync-locker}"
mkdir -p "${PREFIX}/lib" "${PREFIX}/data" "${PREFIX}/panel" "${PREFIX}/.nexus-state"
cp -a "${HERE}/lib/"* "${PREFIX}/lib/"
cp -a "${HERE}/data/"* "${PREFIX}/data/"
cp -a "${HERE}/panel/"* "${PREFIX}/panel/"
chmod +x "${PREFIX}/lib/"*.sh 2>/dev/null || true
export NEXUS_INSTALL_ROOT="${PREFIX}" NEXUS_STATE_DIR="${PREFIX}/.nexus-state"
python3 "${PREFIX}/lib/field-vsync-locker.py" harden
python3 "${PREFIX}/lib/field-vsync-locker.py" launch || true
echo "[vsync-locker] FreeBSD install complete at ${PREFIX}"