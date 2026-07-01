#!/usr/bin/env bash
# Grok AI Lab — bootstrap one sovereign field node (local or free VM worldwide).
set -euo pipefail

INSTALLED=0
REGION="${GROK_LAB_NODE_REGION:-unknown}"
NODE_ID="${GROK_LAB_NODE_ID:-}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --installed) INSTALLED=1; shift ;;
    --region) REGION="$2"; shift 2 ;;
    --node-id) NODE_ID="$2"; shift 2 ;;
    *) shift ;;
  esac
done

DEPLOY="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB="$(cd "$DEPLOY/.." && pwd)"
NL="${NEXUS_INSTALL_ROOT:-$(cd "$LAB/.." && pwd)}"
SG="${SG_ROOT:-$(cd "$NL/.." && pwd)}"
STATE="${NEXUS_STATE_DIR:-$NL/.nexus-state}"
log() { printf '[world-node] %s\n' "$*"; }
PY="${GROK_LAB_PY:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
  PY=python3
fi
export GROK_LAB_PY="$PY"
GROK16="${NL}/Grok16"
if [[ -x "$GROK16/bin/gpy-16" ]]; then
  export GROK16_ROOT="$GROK16" GPY16_ROOT="$GROK16/python" GPY16="$GROK16/bin/gpy-16"
  export GROKPY_ROOT="$GPY16_ROOT" PYTHONG_ROOT="$GPY16_ROOT"
  export PATH="$GROK16/bin:$GROK16/libexec/grok16:$PATH"
  [[ -x "$GROK16/bin/gpy-16" && ! -e "$GROK16/bin/pythong" ]] && ln -sf gpy-16 "$GROK16/bin/pythong"
  PY="$GROK16/bin/gpy-16"
  export GROK_LAB_PY="$PY"
  log "Grok16 runtime — gpy-16 driver"
fi

export SG_ROOT="$SG"
export NEXUS_INSTALL_ROOT="$NL"
export NEXUS_STATE_DIR="$STATE"
export GROK_LAB_ROOT="$LAB"
export GROK_LAB_STATE="${GROK_LAB_STATE:-$LAB/.lab-state}"
export GROK_LAB_WORLD_NODE=1
export NEXUS_BOOT_REKILL=1
export NEXUS_BOOT_REKILL_ONLINE="${NEXUS_BOOT_REKILL_ONLINE:-0}"
export NEXUS_EVERY_KILL_REKILL=1
export ZOCR_REKILL_AT_BOOT=1
export NEXUS_FIELD_STANDALONE=1
export NEXUS_ZNETWORK=1
export NEXUS_ZNETWORK_PROMPT=0

mkdir -p "$STATE" "$GROK_LAB_STATE"

# Headless VM deps (slim bundle — no Grok16)
if command -v apt-get >/dev/null 2>&1; then
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    python3 python3-pip python3-venv python3-pil python3-numpy python3-cryptography \
    curl tesseract-ocr 2>/dev/null || true
fi
"$PY" -m pip install --user -q Pillow numpy cryptography flask 2>/dev/null \
  || "$PY" -m pip install --user --break-system-packages -q Pillow numpy cryptography flask 2>/dev/null \
  || true

if [[ "$INSTALLED" -eq 0 && -f "$NL/scripts/wire-stack.sh" ]]; then
  log "wire-stack (siblings)"
  bash "$NL/scripts/wire-stack.sh" 2>/dev/null || true
fi

log "=== Grok AI Lab world node bootstrap ==="
log "region=$REGION node=$NODE_ID sanctuary=127.0.0.1"

# Stack: panel + Queen + Final Eye + lab desktop
_has_grok16=0
[[ -x "$NL/Grok16/bin/gpy-16" || -x "$NL/Grok16/python/driver/gpy16_driver.py" ]] && _has_grok16=1
if [[ "$_has_grok16" -eq 0 ]]; then
  log "direct-start (python3 — Grok16 not on node yet)"
  bash "$NL/scripts/ammoos-direct-start.sh" 2>&1 | tail -15 || true
elif [[ -x "$NL/scripts/start-field-stack.sh" ]]; then
  log "field-stack (Grok16 gpy-16)"
  NEXUS_FIELD_LAUNCH_BROWSER=0 \
  NEXUS_BOOT_IMPL=0 \
    bash "$NL/scripts/start-field-stack.sh" 2>&1 | tail -20 || true
else
  bash "$NL/scripts/ammoos-direct-start.sh" 2>&1 | tail -10 || true
  EYE="${FINAL_EYE_ROOT:-$SG/Final_Eye}"
  if [[ -f "$EYE/start.sh" ]]; then
    ZOCR_PORT="${FINAL_EYE_PORT:-9479}" bash "$EYE/start.sh" --no-open 2>/dev/null || true
  fi
fi

bash "$LAB/scripts/grok-lab-boot-desktop.sh" 2>&1 | tail -15 || true

# Hostess7 1.0.7h — war-ready web guardian on world nodes
if [[ -f "$NL/Hostess7/scripts/hostess7_web.py" ]]; then
  export HOSTESS7_LICENSE_MODE="${HOSTESS7_LICENSE_MODE:-war}"
  export HOSTESS7_WAR_READY="${HOSTESS7_WAR_READY:-1}"
  export HOSTESS7_ROOT="${HOSTESS7_ROOT:-$NL/Hostess7}"
  export HOSTESS7_BRAIN_STATE="${HOSTESS7_BRAIN_STATE:-$HOSTESS7_ROOT/brain/state}"
  export HOSTESS7_WEB_PORT="${HOSTESS7_WEB_PORT:-8080}"
  PIDF="$HOSTESS7_BRAIN_STATE/hostess7-web.pid"
  LOG="$HOSTESS7_BRAIN_STATE/hostess7-web.log"
  mkdir -p "$(dirname "$LOG")"
  if [[ -f "$PIDF" ]] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
    log "Hostess7 web already running — pid $(cat "$PIDF")"
  else
    log "Hostess7 web-start (war, python3)"
    nohup python3 "$HOSTESS7_ROOT/scripts/hostess7_web.py" >>"$LOG" 2>&1 &
    echo $! >"$PIDF"
  fi
fi

# KILROY war package — armed defensive perimeter + RE-KILL deploy
if [[ -f "$DEPLOY/kilroy-war-arm.sh" && -f "${KILROY_ROOT:-$NL/KILROY}/scripts/build-kilroy.sh" ]]; then
  bash "$DEPLOY/kilroy-war-arm.sh" 2>&1 | tail -8 || true
fi

# Global threat seek — active RE-KILL + auto-rekill loop on world nodes
if [[ "$GROK_LAB_WORLD_NODE" == "1" && -f "$DEPLOY/world-threat-seek.sh" ]]; then
  export GROK_LAB_NODE_REGION="$REGION" GROK_LAB_NODE_ID="$NODE_ID"
  bash "$DEPLOY/world-threat-seek.sh" 2>&1 | tail -8 || true
fi

# Cloudflare edge perimeter — outbound tunnel from loopback sanctuary
if [[ -f "$DEPLOY/cloudflare-world-tunnel.sh" ]]; then
  export GROK_LAB_NODE_REGION="$REGION" GROK_LAB_NODE_ID="$NODE_ID"
  bash "$DEPLOY/cloudflare-world-tunnel.sh" 2>&1 | tail -6 || true
fi

# Final Eye live feed — release vision kills on world nodes, start stream + poll
EYE="${FINAL_EYE_ROOT:-$SG/Final_Eye}"
if [[ -d "$EYE" && -f "$EYE/start.sh" ]]; then
  export GROK_LAB_RELEASE_EYE="${GROK_LAB_RELEASE_EYE:-1}"
  export ZOCR_VIRTUAL_EYE="${ZOCR_VIRTUAL_EYE:-1}"
  export ZOCR_PREFER="${ZOCR_PREFER:-virtual}"
  if [[ "$GROK_LAB_RELEASE_EYE" == "1" && -f "$EYE/zocr_kill.py" ]]; then
    "$PY" "$EYE/zocr_kill.py" release all 2>/dev/null || true
  fi
  if [[ ! -f "$EYE/data/code-seal.json" && -f "$EYE/zocr_security.py" ]]; then
    "$PY" "$EYE/zocr_security.py" seal 2>/dev/null || true
  fi
  if ! curl -sf --connect-timeout 2 "http://127.0.0.1:${FINAL_EYE_PORT:-9479}/api/health" >/dev/null 2>&1; then
    ZOCR_PORT="${FINAL_EYE_PORT:-9479}" ZOCR_VIRTUAL_EYE="${ZOCR_VIRTUAL_EYE:-1}" \
      ZOCR_PREFER="${ZOCR_PREFER:-virtual}" bash "$EYE/start.sh" --no-open 2>/dev/null || true
  fi
  cd "$EYE"
  ZOCR_VIRTUAL_EYE="${ZOCR_VIRTUAL_EYE:-1}" ZOCR_PREFER="${ZOCR_PREFER:-virtual}" \
    "$PY" zocr_watch.py stream-start watch 2>/dev/null || true
  ZOCR_VIRTUAL_EYE="${ZOCR_VIRTUAL_EYE:-1}" "$PY" zocr_watch.py loop >>"$EYE/data/poll.log" 2>&1 &
  stream=$(curl -sf --connect-timeout 3 "http://127.0.0.1:${FINAL_EYE_PORT:-9479}/api/stream/status" 2>/dev/null | head -c 120 || echo down)
  log "Final Eye live — stream=$stream"
fi

# Register on world mesh
export GROK_LAB_NODE_REGION="$REGION"
export GROK_LAB_NODE_ID="$NODE_ID"
"$PY" "$NL/lib/grok-lab-world.py" register-local 2>/dev/null || true

log "Desktop: http://127.0.0.1:${NEXUS_THREAT_PANEL_PORT:-9477}/grok-lab"
log "World node registered — coexist, kill evil, new internet from this home"