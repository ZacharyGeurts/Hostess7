#!/usr/bin/env bash
# sg_build shared helpers
set -euo pipefail

SG_VERSION="${SG_VERSION:-9}"
SG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUDO_PW="${SUDO_PW:-mememe}"
export HOME="${HOME:-/home/default}"

sg_log() { printf '[sg_build v%s] %s\n' "$SG_VERSION" "$*"; }

sg_sudo() {
  printf '%s\n' "$SUDO_PW" | sudo -S -p '' "$@" 2>/dev/null || true
}

sg_service_off() {
  local unit="$1"
  sg_sudo systemctl stop "$unit" 2>/dev/null || true
  sg_sudo systemctl disable "$unit" 2>/dev/null || true
  sg_sudo systemctl mask "$unit" 2>/dev/null || true
}

sg_kill_pattern() {
  pkill -f "$1" 2>/dev/null || true
}

# legacy aliases (old scripts / wrappers)
ammo_log() { sg_log "$@"; }
ammo_sudo() { sg_sudo "$@"; }
ammo_service_off() { sg_service_off "$@"; }
ammo_kill_pattern() { sg_kill_pattern "$@"; }
AMMO_ROOT="$SG_ROOT"
AMMO_VERSION="$SG_VERSION"