#!/usr/bin/env bash
# Legacy open + secured — promote Truth DNS + Field DHCP to primary (Dreamcast modem welcome).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
export NEXUS_LEGACY_OPEN_SECURED=1
export NEXUS_FIELD_DNS_LEGACY_COMPAT=1
export NEXUS_FIELD_DHCP_LEGACY_DNS_IPV4="${NEXUS_FIELD_DHCP_LEGACY_DNS_IPV4:-192.168.47.1}"
export NEXUS_QUEEN_LAN_DNS="${NEXUS_QUEEN_LAN_DNS:-192.168.47.1}"
PY="${PYTHON:-python3}"
if [[ -x "$ROOT/scripts/queen-lan-up.sh" ]] && [[ "$(id -u)" -eq 0 ]]; then
  bash "$ROOT/scripts/queen-lan-up.sh"
elif [[ -x "$ROOT/scripts/queen-lan-up.sh" ]] && command -v sudo >/dev/null 2>&1; then
  sudo -n bash "$ROOT/scripts/queen-lan-up.sh" 2>/dev/null || true
fi
exec "$PY" "$ROOT/lib/field-legacy-connect.py" ensure-primary