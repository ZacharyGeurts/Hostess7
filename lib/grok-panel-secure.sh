# AmmoLang boundary route — AML_BUILD=1 universal boundary
_aml_find_root() {
  local d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  while [[ "$d" != "/" ]]; do
    [[ -f "$d/lib/ammolang-run.sh" ]] && echo "$d" && return 0
    d="$(dirname "$d")"
  done
  return 1
}
if [[ "${AML_BUILD:-1}" != "0" ]] && [[ -z "${AML_BOUNDARY_ACTIVE:-}" ]]; then
  _AML_ROOT="$(_aml_find_root 2>/dev/null || true)"
  if [[ -n "$_AML_ROOT" ]]; then
    export AML_BOUNDARY_ACTIVE=1
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/grok-panel-secure.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Secure Grok panel — loopback panel + field-grok ACP + GNU terminal UI.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="${NEXUS_STATE_DIR:-${ROOT}/.nexus-state}"
PORT="${NEXUS_THREAT_PANEL_PORT:-9477}"
PY="${PYTHON:-python3}"
FIELD_GROK="${ROOT}/lib/bin/field-grok"
TOKEN_FILE="${HOME}/.config/sg/field-grok-token"
AI_TOKEN_FILE="${STATE}/ai-integration.token"

log() { printf '[grok-panel] %s\n' "$*"; }

export NEXUS_INSTALL_ROOT="${ROOT}"
export NEXUS_STATE_DIR="${STATE}"
export SG_ROOT="${SG_ROOT:-$(dirname "${ROOT}")}"
export GROK_HOME="${GROK_HOME:-${HOME}/.grok}"
export GROK_MAX_SOCKETS="${GROK_MAX_SOCKETS:-5}"
export NEXUS_AI_SECURE_CHANNEL=1
export QUEEN_AI_TELEMETRY_OK=1
export QUEEN_GROK_BUILD=1
export QUEEN_GROK_BUILD_SECURE=1
export GROK_SECURE_CHANNEL=1
export SSL_CERT_FILE="${SSL_CERT_FILE:-/etc/ssl/certs/ca-certificates.crt}"
export REQUESTS_CA_BUNDLE="${REQUESTS_CA_BUNDLE:-$SSL_CERT_FILE}"
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy ALL_PROXY all_proxy 2>/dev/null || true

mkdir -p "${STATE}" "${HOME}/.config/sg"

# Operator + AI tokens (panel API guard)
if [[ ! -f "${TOKEN_FILE}" ]]; then
  "${PY}" "${ROOT}/lib/field-grok-cli.py" token >/dev/null
fi
if [[ ! -f "${AI_TOKEN_FILE}" ]]; then
  "${PY}" -c "
import importlib.util, sys
from pathlib import Path
p = Path('${ROOT}/lib/ai-integration-hook.py')
spec = importlib.util.spec_from_file_location('ai_hook', p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print(mod._integration_token())
" >/dev/null 2>&1 || true
fi

OPERATOR_TOKEN="$(cat "${TOKEN_FILE}" 2>/dev/null || true)"
AI_TOKEN="$(cat "${AI_TOKEN_FILE}" 2>/dev/null || true)"

# Panel ensure
panel_py="${ROOT}/lib/threat-panel-http.py"
if ! pgrep -f "threat-panel-http.py.*${PORT}" >/dev/null 2>&1; then
  log "starting NEXUS panel on :${PORT}"
  nohup env \
    NEXUS_INSTALL_ROOT="${ROOT}" \
    NEXUS_STATE_DIR="${STATE}" \
    NEXUS_AI_SECURE_CHANNEL=1 \
    QUEEN_AI_TELEMETRY_OK=1 \
    QUEEN_GROK_BUILD=1 \
    QUEEN_GROK_BUILD_SECURE=1 \
    GROK_SECURE_CHANNEL=1 \
    "${PY}" "${panel_py}" "${PORT}" "${ROOT}/panel" "${STATE}/threat-panel.json" \
    >>"${STATE}/panel-http.log" 2>&1 &
  for _ in $(seq 1 20); do
    curl -sf "http://127.0.0.1:${PORT}/field-gnu-terminal" >/dev/null 2>&1 && break
    sleep 0.25
  done
else
  log "panel already on :${PORT}"
fi

# Secure field-grok posture + ACP
if [[ -x "${FIELD_GROK}" ]]; then
  log "field-grok posture"
  "${FIELD_GROK}" json | "${PY}" -c "import json,sys; d=json.load(sys.stdin); print('  secure=',d.get('secure_channel'),' acp=',d.get('acp',{}).get('ws_url'))" 2>/dev/null || "${FIELD_GROK}" json | head -c 200
  echo
  if [[ -n "${OPERATOR_TOKEN}" ]]; then
    ACP_OUT="$(printf '{"action":"acp-start","token":"%s"}' "${OPERATOR_TOKEN}" | "${FIELD_GROK}" dispatch 2>/dev/null || true)"
    if echo "${ACP_OUT}" | grep -q '"ok": true'; then
      log "ACP started $(echo "${ACP_OUT}" | "${PY}" -c "import json,sys; d=json.load(sys.stdin); print('pid',d.get('pid','?'))" 2>/dev/null || echo ok)"
    else
      log "ACP dispatch: ${ACP_OUT:-skipped}"
    fi
  fi
else
  log "WARN: ${FIELD_GROK} missing — run packaging/field-grok/linux/install.sh"
fi

PANEL_URL="http://127.0.0.1:${PORT}/field-gnu-terminal"
API_URL="http://127.0.0.1:${PORT}/api/field-grok"
ACP_URL="ws://127.0.0.1:2419"

log "=== secure grok panel ready ==="
log "terminal UI:  ${PANEL_URL}"
log "field-grok API: ${API_URL}"
log "ACP websocket:  ${ACP_URL}"
log ""
log "bash one-liners:"
log "  export NEXUS_INSTALL_ROOT='${ROOT}' FIELD_GROK_OPERATOR_TOKEN='${OPERATOR_TOKEN}'"
log "  field-grok json"
log "  curl -s -H 'X-Nexus-AI-Actor: ai' -H 'X-Nexus-AI-Token: ${AI_TOKEN}' ${API_URL}"
log ""

if command -v xdg-open >/dev/null 2>&1 && [[ "${GROK_PANEL_OPEN_BROWSER:-1}" == "1" ]]; then
  xdg-open "${PANEL_URL}" >/dev/null 2>&1 &
  log "opened browser → ${PANEL_URL}"
fi