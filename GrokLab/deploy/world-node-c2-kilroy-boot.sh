#!/usr/bin/env bash
# World node boot — NEXUS C2 command deck + KILROY PC core only (no Queen kiosk).
set -euo pipefail
export AML_BUILD=0

NL="${NEXUS_INSTALL_ROOT:-/opt/ammoos/ammoos/NewLatest}"
SG="${SG_ROOT:-/opt/ammoos/ammoos}"
STATE="${NEXUS_STATE_DIR:-$NL/.nexus-state}"
DEPLOY="${NL}/GrokLab/deploy"
PY="${GROK_LAB_PY:-python3}"

export SG_ROOT="$SG" NEXUS_INSTALL_ROOT="$NL" NEXUS_STATE_DIR="$STATE"
export NEXUS_WAR_MACHINE=1 NEXUS_C2_WAR_POSTURE=1 NEXUS_C2_KIOSK=0
export NEXUS_EVERY_KILL_REKILL=1 NEXUS_BOOT_REKILL=1 NEXUS_FIELD_ATTACK_KIT=1
export NEXUS_FIELD_AUTO_REKILL=1 NEXUS_ATTACK_KIT_AUTO_CRUSH=1 NEXUS_KILL_DETECT=1
export KILROY_WAR_POSTURE=1 KILROY_PC_CORE=1 GROK_LAB_WORLD_NODE=1
export NEXUS_FIELD_STANDALONE=1 NEXUS_ZNETWORK=1 NEXUS_ZNETWORK_PROMPT=0
export FIELD_STACK_LAYER="hardware,nexus_c2,kilroy"

mkdir -p "$STATE"

# World nodes get slim Grok16 rsync (no grok_core) — gpy-16 crashes the panel.
if [[ -z "${GROK_LAB_PY:-}" ]]; then
  if [[ "${GROK_LAB_WORLD_NODE:-0}" == "1" ]]; then
    PY="python3"
  elif [[ -x "$NL/Grok16/bin/gpy-16" ]] && "$NL/Grok16/bin/gpy-16" -c 'import grok_core' 2>/dev/null; then
    PY="$NL/Grok16/bin/gpy-16"
    export PATH="$NL/Grok16/bin:$PATH"
  fi
fi

log() { printf '[c2-kilroy-boot] %s\n' "$*"; }

# shellcheck source=/dev/null
[[ -f "$NL/lib/field-war-hardening.sh" ]] && AML_BUILD=0 source "$NL/lib/field-war-hardening.sh" && nexus_field_war_harden || true

if [[ -x "$DEPLOY/kilroy-war-arm.sh" ]]; then
  AML_BUILD=0 bash "$DEPLOY/kilroy-war-arm.sh" 2>&1 | tail -6 || true
fi

if [[ ! -f "$STATE/threat-panel.json" && -f "$NL/scripts/panel-json-assemble.py" ]]; then
  NEXUS_INSTALL_ROOT="$NL" NEXUS_STATE_DIR="$STATE" "$PY" "$NL/scripts/panel-json-assemble.py" >/dev/null 2>&1 || true
fi

if ! pgrep -f 'threat-panel-http.py.*9477' >/dev/null 2>&1; then
  log "starting NEXUS C2 panel :9477"
  nohup env NEXUS_INSTALL_ROOT="$NL" NEXUS_STATE_DIR="$STATE" SG_ROOT="$SG" \
    "$PY" "$NL/lib/threat-panel-http.py" 9477 "$NL/panel" "$STATE/threat-panel.json" \
    >>"$STATE/panel-http.log" 2>&1 &
fi

if [[ -f "$NL/lib/kilroy-boot-services.py" ]]; then
  timeout 15 "$PY" "$NL/lib/kilroy-boot-services.py" board >/dev/null 2>&1 || true
fi
if [[ -f "$NL/lib/kilroy-field-brain.py" ]]; then
  timeout 15 "$PY" "$NL/lib/kilroy-field-brain.py" board >/dev/null 2>&1 || true
fi

if [[ -f "$DEPLOY/world-threat-seek.sh" ]]; then
  bash "$DEPLOY/world-threat-seek.sh" 2>&1 | tail -4 || true
fi

log "NEXUS C2 + KILROY war node up"