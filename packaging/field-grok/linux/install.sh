#!/usr/bin/env bash
# Install field-grok secure CLI binary + operator token.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
PW="${HOSTESS7_SUDO_PW:-mememe}"
PY="${PYTHON:-python3}"
BIN="${ROOT}/lib/bin/field-grok"
TOKEN_DIR="${HOME}/.config/sg"

log() { printf '[FieldGrok] %s\n' "$*"; }

cd "${ROOT}/src/field-grok"
make GROK16_ROOT="${GROK16_ROOT:-${ROOT}/Grok16}" all

chmod +x "${ROOT}/lib/field-grok-cli.py"
mkdir -p "${TOKEN_DIR}"
"${PY}" "${ROOT}/lib/field-grok-cli.py" token >/dev/null

if command -v sudo >/dev/null 2>&1 && echo "$PW" | sudo -S -v 2>/dev/null; then
  log "optional: link into /usr/local/bin"
  echo "$PW" | sudo -S ln -sf "${BIN}" /usr/local/bin/field-grok 2>/dev/null || true
fi

log "installed ${BIN}"
log "status: ${BIN} json"
log "token:  ${TOKEN_DIR}/field-grok-token"
log "api:    http://127.0.0.1:9477/api/field-grok"