#!/usr/bin/env bash
# Ensure NEXUS threat panel is listening on loopback :9477 (sanctuary or world node).
set -euo pipefail
export AML_BUILD=0
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

NL="${NEXUS_INSTALL_ROOT:-/opt/ammoos/ammoos/NewLatest}"
STATE="${NEXUS_STATE_DIR:-$NL/.nexus-state}"
SG="${SG_ROOT:-$(dirname "$NL")}"
PORT="${NEXUS_THREAT_PANEL_PORT:-9477}"
WAIT_SEC="${NEXUS_PANEL_ENSURE_WAIT_SEC:-45}"

log() { printf '[panel-ensure] %s\n' "$*"; }

if [[ "${GROK_LAB_WORLD_NODE:-0}" == "1" ]]; then
  PY="${GROK_LAB_PY:-python3}"
else
  PY="$(command -v pythong 2>/dev/null || command -v python3 2>/dev/null || true)"
fi
[[ -n "$PY" ]] || { log "FAIL — no python"; exit 1; }

[[ -f "$NL/lib/threat-panel-http.py" && -d "$NL/panel" ]] || {
  log "FAIL — panel tree missing under $NL"
  exit 1
}

mkdir -p "$STATE"

if [[ ! -f "$STATE/threat-panel.json" && -f "$NL/scripts/panel-json-assemble.py" ]]; then
  NEXUS_INSTALL_ROOT="$NL" NEXUS_STATE_DIR="$STATE" \
    "$PY" "$NL/scripts/panel-json-assemble.py" >/dev/null 2>&1 || true
fi

if ! pgrep -f "threat-panel-http.py.*${PORT}" >/dev/null 2>&1; then
  log "starting NEXUS panel :${PORT}"
  nohup env \
    NEXUS_INSTALL_ROOT="$NL" \
    NEXUS_STATE_DIR="$STATE" \
    SG_ROOT="$SG" \
    TDIR="${TDIR:-}" \
    "$PY" "$NL/lib/threat-panel-http.py" "$PORT" "$NL/panel" "$STATE/threat-panel.json" \
    >>"$STATE/panel-http.log" 2>&1 &
fi

for _ in $(seq 1 "$WAIT_SEC"); do
  code="$(curl -sf -o /dev/null -w '%{http_code}' --connect-timeout 1 --max-time 2 \
    "http://127.0.0.1:${PORT}/field" 2>/dev/null || echo 000)"
  if [[ "$code" == "200" ]]; then
    log "panel ready :${PORT}"
    exit 0
  fi
  sleep 1
done

log "WARN — panel not HTTP 200 after ${WAIT_SEC}s (see ${STATE}/panel-http.log)"
exit 1