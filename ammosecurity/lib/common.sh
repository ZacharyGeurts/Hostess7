#!/usr/bin/env bash
# sg_build shared helpers
set -euo pipefail

SG_VERSION="${SG_VERSION:-9}"
SG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SUDO_PW="${SUDO_PW:-mememe}"
export HOME="${HOME:-/home/default}"

AMMO_STATE_DIR="${AMMO_STATE_DIR:-/var/lib/ammosecurity}"
AMMO_PREFS_DIR="${AMMO_PREFS_DIR:-${HOME}/.config/ammo-shield}"
AMMO_VIOLATIONS_LOG="${AMMO_VIOLATIONS_LOG:-${AMMO_STATE_DIR}/violations.log}"
AMMO_HEALTH_LOG="${AMMO_HEALTH_LOG:-${AMMO_STATE_DIR}/health.log}"

sg_log() { printf '[sg_build v%s] %s\n' "$SG_VERSION" "$*"; }

ammo_ensure_state() {
  mkdir -p "$AMMO_STATE_DIR" "$AMMO_PREFS_DIR" 2>/dev/null || true
  ammo_sudo mkdir -p "$AMMO_STATE_DIR" 2>/dev/null || true
}

ammo_violation() {
  local msg="$1"
  ammo_ensure_state
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date)"
  printf '%s VIOLATION %s\n' "$ts" "$msg" >>"${AMMO_VIOLATIONS_LOG}" 2>/dev/null \
    || printf '%s VIOLATION %s\n' "$ts" "$msg" >>"${HOME}/.ammo-violations.log" 2>/dev/null || true
  sg_log "VIOLATION: $msg"
}

ammo_health_note() {
  local msg="$1"
  ammo_ensure_state
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date)"
  printf '%s HEALTH %s\n' "$ts" "$msg" >>"${AMMO_HEALTH_LOG}" 2>/dev/null \
    || printf '%s HEALTH %s\n' "$ts" "$msg" >>"${HOME}/.ammo-health.log" 2>/dev/null || true
}

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