#!/usr/bin/env bash
# VSYNC-Locker Linux install — portable or system path.
set -euo pipefail

HERE="$(cd "$(dirname "$0")/../.." && pwd)"
PREFIX="${VSYNC_INSTALL_ROOT:-${NEXUS_INSTALL_ROOT:-/opt/vsync-locker}}"

echo "[vsync-locker] installing to ${PREFIX}"
sudo mkdir -p "${PREFIX}/lib" "${PREFIX}/data" "${PREFIX}/panel" "${PREFIX}/.nexus-state"
sudo cp -a "${HERE}/lib/field-vsync-locker.py" \
  "${HERE}/lib/field-vsync-locker-launch.sh" \
  "${HERE}/lib/field-vsync-locker-guard.sh" \
  "${PREFIX}/lib/"
[[ -f "${HERE}/lib/hardware_wire_registry.py" ]] && \
  sudo cp -a "${HERE}/lib/hardware_wire_registry.py" "${PREFIX}/lib/"
sudo cp -a "${HERE}/data/field-vsync-locker-doctrine.json" \
  "${HERE}/data/field-vsync-locker-version.json" \
  "${HERE}/data/field-vsync-locker-platform-release.json" \
  "${PREFIX}/data/"
sudo cp -a "${HERE}/panel/field-vsync-locker.desktop" "${PREFIX}/panel/"
[[ -x "${HERE}/bin/vsync-launch" ]] && sudo install -m 755 "${HERE}/bin/vsync-launch" "${PREFIX}/bin/vsync-launch"
sudo chmod +x "${PREFIX}/lib/field-vsync-locker-launch.sh" "${PREFIX}/lib/field-vsync-locker-guard.sh"

export NEXUS_INSTALL_ROOT="${PREFIX}"
export NEXUS_STATE_DIR="${PREFIX}/.nexus-state"
python3 "${PREFIX}/lib/field-vsync-locker.py" harden
python3 "${PREFIX}/lib/field-vsync-locker.py" install-desktop
python3 "${PREFIX}/lib/field-vsync-locker.py" launch || true

if [[ -f "${HERE}/packaging/linux/vsync-locker.service" ]]; then
  sed "s|__PREFIX__|${PREFIX}|g" "${HERE}/packaging/linux/vsync-locker.service" > /tmp/vsync-locker.service
  mkdir -p "${HOME}/.config/systemd/user"
  cp /tmp/vsync-locker.service "${HOME}/.config/systemd/user/vsync-locker.service"
  systemctl --user daemon-reload 2>/dev/null || true
  systemctl --user enable --now vsync-locker.service 2>/dev/null || true
fi

echo "[vsync-locker] installed — double-click VSYNC Locker or: python3 ${PREFIX}/lib/field-vsync-locker.py guard --status"