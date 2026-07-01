#!/usr/bin/env bash
# World field nodes — active global threat seek + RE-KILL deploy.
set -euo pipefail

NL="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
SG="${SG_ROOT:-$(cd "$NL/.." && pwd)}"
STATE="${NEXUS_STATE_DIR:-$NL/.nexus-state}"
DEPLOY="$(cd "$(dirname "$0")" && pwd)"
PY="${GROK_LAB_PY:-python3}"
REGION="${GROK_LAB_NODE_REGION:-unknown}"
NODE_ID="${GROK_LAB_NODE_ID:-world-node}"

log() { printf '[world-threat] %s\n' "$*"; }

export SG_ROOT="$SG" NEXUS_INSTALL_ROOT="$NL" NEXUS_STATE_DIR="$STATE"
export NEXUS_FIELD_ATTACK_KIT=1 NEXUS_BOOT_REKILL=1 NEXUS_EVERY_KILL_REKILL=1
export KILROY_WAR_POSTURE=1 KILROY_DEFENSIVE_ONLY=1 KILROY_WAR_SCOPE=defensive_perimeter

if [[ -x "$NL/Grok16/bin/gpy-16" ]]; then
  export PATH="$NL/Grok16/bin:$PATH"
  [[ ! -e "$NL/Grok16/bin/pythong" ]] && ln -sf gpy-16 "$NL/Grok16/bin/pythong"
  PY="$NL/Grok16/bin/gpy-16"
fi

mkdir -p "$STATE"
log "=== global threat seek — region=$REGION node=$NODE_ID ==="

hostile=0
[[ -f "$STATE/field-hostile.tsv" ]] && hostile=$(wc -l <"$STATE/field-hostile.tsv" | tr -d ' ')
log "hostile list: $hostile entries"

# RE-KILL all registered at boot + revalidate kill list
if [[ -f "$NL/lib/field-attack-kit.py" ]]; then
  export NEXUS_BOOT_REKILL_ONLINE="${NEXUS_BOOT_REKILL_ONLINE:-1}"
  boot=$(timeout 45 "$PY" "$NL/lib/field-attack-kit.py" boot-rekill 2>/dev/null || echo '{}')
  rek=$(echo "$boot" | "$PY" -c "import sys,json;d=json.load(sys.stdin);print(d.get('rekill',{}).get('rekilled_count',0))" 2>/dev/null || echo 0)
  log "boot-rekill — rekilled=$rek"
  # Seek online validated threats globally
  seek=$(timeout 60 "$PY" "$NL/lib/field-attack-kit.py" auto-rekill 2>/dev/null || echo '{}')
  sought=$(echo "$seek" | "$PY" -c "import sys,json;d=json.load(sys.stdin);print(d.get('rekilled_count',d.get('attempted',0)))" 2>/dev/null || echo 0)
  log "auto-rekill seek — $sought"
fi

# Non-Field-1 scan → hostile → bring to Field 1
if [[ -f "$DEPLOY/field-one-world-bring.sh" ]]; then
  export GROK_LAB_NODE_REGION="$REGION" GROK_LAB_NODE_ID="$NODE_ID"
  bash "$DEPLOY/field-one-world-bring.sh" 2>&1 | tail -6 || true
fi

# Planetary DNS security posture
if [[ -f "$NL/lib/dns-planetary-security.py" ]]; then
  timeout 15 "$PY" "$NL/lib/dns-planetary-security.py" json >/dev/null 2>&1 || true
fi

# Background seek loop — every 15 min on world nodes
LOOP_PIDFILE="$STATE/world-threat-seek.pid"
if [[ ! -f "$LOOP_PIDFILE" ]] || ! kill -0 "$(cat "$LOOP_PIDFILE" 2>/dev/null)" 2>/dev/null; then
  nohup bash -c "
    export SG_ROOT='$SG' NEXUS_INSTALL_ROOT='$NL' NEXUS_STATE_DIR='$STATE'
    export NEXUS_FIELD_ATTACK_KIT=1 NEXUS_BOOT_REKILL=1 PATH='$NL/Grok16/bin:'\$PATH
    PY='$PY'
    while true; do
      timeout 90 \"\$PY\" '$NL/lib/field-attack-kit.py' auto-rekill >/dev/null 2>&1 || true
      if [[ -f '$DEPLOY/field-one-world-bring.sh' ]]; then
        bash '$DEPLOY/field-one-world-bring.sh' >/dev/null 2>&1 || true
      fi
      sleep 900
    done
  " >>"$STATE/world-threat-seek.log" 2>&1 &
  echo $! >"$LOOP_PIDFILE"
  log "seek loop started pid=$(cat "$LOOP_PIDFILE")"
fi

ts=$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u)
cat >"$STATE/world-threat-seek.json" <<EOF
{"schema":"world-threat-seek/v1","updated":"${ts}","node_id":"${NODE_ID}","region":"${REGION}","active":true,"seeking_globally":true,"hostile_entries":${hostile},"boot_rekill":true,"auto_rekill_loop":true,"perimeter":"defensive_only","loopback_authority":"127.0.0.1"}
EOF
log "global threat seek ACTIVE — defensive perimeter, stack corroboration only"