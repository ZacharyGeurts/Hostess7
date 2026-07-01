#!/usr/bin/env bash
# Cloudflare Tunnel — propagate loopback Grok Lab perimeter through CF edge (outbound only).
set -euo pipefail

DEPLOY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NL="${NEXUS_INSTALL_ROOT:-$(cd "$DEPLOY/../../.." && pwd)}"
SG="${SG_ROOT:-$(cd "$NL/.." && pwd)}"
STATE="${NEXUS_STATE_DIR:-$NL/.nexus-state}"
CF_DIR="$DEPLOY/cloudflare"
CFG="$DEPLOY/cloudflare-world-config.json"
PIDFILE="$STATE/cloudflare-tunnel.pid"
LOG="$STATE/cloudflare-tunnel.log"
REGION="${GROK_LAB_NODE_REGION:-local}"
NODE_ID="${GROK_LAB_NODE_ID:-node-local}"
PANEL_PORT="${NEXUS_THREAT_PANEL_PORT:-9477}"
EYE_PORT="${FINAL_EYE_PORT:-9479}"

log() { printf '[cloudflare-world] %s\n' "$*"; }

_install_cloudflared() {
  local bin="${CLOUDFLARED_BIN:-}"
  if [[ -n "$bin" && -x "$bin" ]]; then
    echo "$bin"
    return 0
  fi
  if command -v cloudflared >/dev/null 2>&1; then
    command -v cloudflared
    return 0
  fi
  if [[ -x /tmp/cloudflared ]]; then
    echo /tmp/cloudflared
    return 0
  fi
  local arch
  arch=$(uname -m)
  case "$arch" in
    x86_64|amd64) arch=amd64 ;;
    aarch64|arm64) arch=arm64 ;;
    *) arch=amd64 ;;
  esac
  local dest="$CF_DIR/bin/cloudflared"
  mkdir -p "$CF_DIR/bin"
  if [[ ! -x "$dest" ]]; then
    log "downloading cloudflared ($arch)…"
    curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${arch}" -o "$dest"
    chmod +x "$dest"
  fi
  echo "$dest"
}

_read_token() {
  if [[ -n "${CLOUDFLARE_TUNNEL_TOKEN:-}" ]]; then
    echo "$CLOUDFLARE_TUNNEL_TOKEN"
    return 0
  fi
  local tf="$CF_DIR/tunnel.token"
  [[ -f "$tf" ]] && tr -d ' \n' <"$tf" && return 0
  return 1
}

_write_state() {
  local mode="$1" active="$2" tunnel_pid="${3:-}"
  local ts
  ts=$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u)
  mkdir -p "$STATE"
  cat >"$STATE/cloudflare-world.json" <<EOF
{"schema":"cloudflare-world/v1","updated":"${ts}","node_id":"${NODE_ID}","region":"${REGION}","mode":"${mode}","active":${active},"tunnel_pid":${tunnel_pid:-null},"perimeter":"defensive_only","loopback_authority":"127.0.0.1","ingress":["http://127.0.0.1:${PANEL_PORT}/grok-lab","http://127.0.0.1:${PANEL_PORT}/field","http://127.0.0.1:${EYE_PORT}/ops"],"propagating_globally":true,"seeking_threat_via_edge":true}
EOF
}

CFD="$(_install_cloudflared)"
log "cloudflared=$CFD region=$REGION node=$NODE_ID"

if ! TOKEN="$(_read_token 2>/dev/null || true)" || [[ -z "${TOKEN:-}" ]]; then
  log "STANDBY — no tunnel token (set CLOUDFLARE_TUNNEL_TOKEN or $CF_DIR/tunnel.token)"
  _write_state standby false
  log "Create tunnel: Cloudflare Zero Trust → Networks → Tunnels → Create → copy token"
  exit 0
fi

# Loopback stack must be up before tunnel carries traffic
grok_ok=0 eye_ok=0
curl -sf --connect-timeout 2 "http://127.0.0.1:${PANEL_PORT}/grok-lab" >/dev/null 2>&1 && grok_ok=1
curl -sf --connect-timeout 2 "http://127.0.0.1:${EYE_PORT}/api/health" >/dev/null 2>&1 && eye_ok=1
log "loopback grok=$grok_ok eye=$eye_ok"

if [[ -f "$PIDFILE" ]]; then
  old=$(cat "$PIDFILE" 2>/dev/null || true)
  if [[ -n "$old" ]] && kill -0 "$old" 2>/dev/null; then
    log "tunnel already running pid=$old"
    _write_state active true "$old"
    exit 0
  fi
fi

mkdir -p "$STATE"
nohup "$CFD" tunnel --no-autoupdate run --token "$TOKEN" >>"$LOG" 2>&1 &
echo $! >"$PIDFILE"
sleep 2
pid=$(cat "$PIDFILE")
if kill -0 "$pid" 2>/dev/null; then
  log "tunnel ACTIVE pid=$pid — perimeter on Cloudflare edge"
  _write_state active true "$pid"
else
  log "tunnel failed — see $LOG"
  _write_state failed false
  tail -5 "$LOG" 2>/dev/null || true
  exit 1
fi