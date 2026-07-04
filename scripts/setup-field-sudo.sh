#!/usr/bin/env bash
# Secure sudo for humans (password) + AI communique (scoped NOPASSWD wrapper).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PW="${HOSTESS7_SUDO_PW:-mememe}"
CFG_DIR="${HOME}/.config/ammo-shield"
SUDO_ENV="${CFG_DIR}/sudo.env"
AI_ENV="${CFG_DIR}/ai-sudo.env"
WRAPPER_SRC="${ROOT}/scripts/hostess7-field-sudo.sh"
WRAPPER_DST="/usr/local/bin/hostess7-field-sudo"
SUDOERS="/etc/sudoers.d/99-hostess7-field"
USER_NAME="$(id -un)"

log() { printf '[setup-field-sudo] %s\n' "$*"; }

if ! echo "$PW" | sudo -S -v 2>/dev/null; then
  log "ERROR: sudo password required — set HOSTESS7_SUDO_PW or enter mememe when prompted"
  exit 1
fi

log "install human + AI sudo config"
mkdir -p "$CFG_DIR"
chmod 700 "$CFG_DIR"
umask 077
cat >"$SUDO_ENV" <<EOF
# Hostess7 sudo — humans + AI communique (mode 600 — never commit)
HOSTESS7_SUDO_PW=${PW}
NEXUS_INSTALL_ROOT=${ROOT}
NEXUS_STATE_DIR=${ROOT}/.nexus-state
EOF
chmod 600 "$SUDO_ENV"

cat >"$AI_ENV" <<EOF
# AI communique lane — sources human sudo config
source "${SUDO_ENV}"
export HOSTESS7_AI_COMMUNIQUE=1
export HOSTESS7_AI_PRIMARY=1
EOF
chmod 600 "$AI_ENV"

log "install wrapper → ${WRAPPER_DST}"
sudo install -m 755 "$WRAPPER_SRC" "$WRAPPER_DST"

log "install sudoers drop-in (scoped NOPASSWD)"
sudo tee "$SUDOERS" >/dev/null <<EOF
# Hostess7 field stack — scoped elevation for humans + AI communique
# Password sudo: any human in %sudo (default password mememe)
# NOPASSWD: only hostess7-field-sudo wrapper (allowlist inside)

Cmnd_Alias HOSTESS7_FIELD = ${WRAPPER_DST}, ${WRAPPER_DST} *

%sudo ALL=(root) NOPASSWD: HOSTESS7_FIELD
${USER_NAME} ALL=(root) NOPASSWD: HOSTESS7_FIELD
EOF
sudo chmod 440 "$SUDOERS"
if command -v visudo >/dev/null 2>&1; then
  sudo visudo -c -f "$SUDOERS"
fi

log "verify lanes"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
# shellcheck source=/dev/null
source "$SUDO_ENV"
sudo -n "$WRAPPER_DST" verify | python3 -c "import json,sys; d=json.load(sys.stdin); print('nopasswd_ok:', d.get('ok')); print('actions:', len(d.get('actions') or []))"

log "done — humans: sudo + password mememe · AI: hostess7-field-sudo run <action>"