#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")/../.." && pwd)"
PREFIX="${VSYNC_INSTALL_ROOT:-${HOME}/Applications/VSYNC-Locker}"
mkdir -p "${PREFIX}/lib" "${PREFIX}/data" "${PREFIX}/panel" "${PREFIX}/.nexus-state"
cp -a "${HERE}/lib/"* "${PREFIX}/lib/"
cp -a "${HERE}/data/"* "${PREFIX}/data/"
cp -a "${HERE}/panel/"* "${PREFIX}/panel/"
chmod +x "${PREFIX}/lib/"*.sh 2>/dev/null || true
export NEXUS_INSTALL_ROOT="${PREFIX}" NEXUS_STATE_DIR="${PREFIX}/.nexus-state"
python3 "${PREFIX}/lib/field-vsync-locker.py" harden
python3 "${PREFIX}/lib/field-vsync-locker.py" launch || true
if [[ -f "${HERE}/packaging/macos/com.field.vsync-locker.plist" ]]; then
  sed "s|__PREFIX__|${PREFIX}|g" "${HERE}/packaging/macos/com.field.vsync-locker.plist" > "${HOME}/Library/LaunchAgents/com.field.vsync-locker.plist"
  launchctl unload "${HOME}/Library/LaunchAgents/com.field.vsync-locker.plist" 2>/dev/null || true
  launchctl load "${HOME}/Library/LaunchAgents/com.field.vsync-locker.plist" 2>/dev/null || true
fi
echo "[vsync-locker] macOS install complete at ${PREFIX}"