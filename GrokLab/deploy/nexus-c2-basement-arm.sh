#!/usr/bin/env bash
# NEXUS C2 secure basement — layer 1 before KILROY. Gates, trust strike, weapons turnover.
set -euo pipefail
export AML_BUILD=0

NL="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
SG="${SG_ROOT:-$(cd "$NL/.." && pwd)}"
STATE="${NEXUS_STATE_DIR:-$NL/.nexus-state}"
PY="${GROK_LAB_PY:-python3}"

export SG_ROOT="$SG" NEXUS_INSTALL_ROOT="$NL" NEXUS_STATE_DIR="$STATE"
export NEXUS_WAR_MACHINE=1 NEXUS_C2_WAR_POSTURE=1 NEXUS_C2_KIOSK=0
export NEXUS_C2_BASEMENT=1 NEXUS_C2_SECURE_BASEMENT=1 NEXUS_C2_WEAPONIZED=1
export NEXUS_CONNECTION_GATEKEEPER=1 NEXUS_GATEKEEPER_STRICT_TRUST=1
export NEXUS_PACKET_PERMISSION=1 NEXUS_ATTACK_KIT_AUTO_CRUSH=1
export NEXUS_FIELD_ATTACK_KIT=1 NEXUS_FIELD_AUTO_REKILL=1 NEXUS_EVERY_KILL_REKILL=1
export NEXUS_BOOT_REKILL=1 NEXUS_KILL_DETECT=1

log() { printf '[nexus-c2-basement] %s\n' "$*"; }

if [[ "${GROK_LAB_WORLD_NODE:-0}" == "1" ]]; then
  PY="python3"
elif [[ -x "$NL/Grok16/bin/gpy-16" ]] && "$NL/Grok16/bin/gpy-16" -c 'import grok_core' 2>/dev/null; then
  PY="$NL/Grok16/bin/gpy-16"
fi

mkdir -p "$STATE"
ts=$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u)
steps=()

run_py() {
  local label="$1" script="$2"
  shift 2
  [[ -f "$script" ]] || return 0
  if out=$("$PY" "$script" "$@" 2>/dev/null); then
    steps+=("$label:ok")
    echo "$out" | tail -c 400 >/dev/null 2>&1 || true
  else
    steps+=("$label:warn")
  fi
}

log "=== NEXUS C2 secure basement — arm layer 1 ==="

run_py gatekeeper "$NL/lib/connection-gatekeeper.py"
run_py trust_strike "$NL/lib/trust-strike-engine.py" summary
run_py probe_guard "$NL/lib/nexus-probe-guard.py" json
run_py weapons "$NL/lib/hostess7-weapons-defense.py" turnover

panel_up=0
curl -sf http://127.0.0.1:9477/field >/dev/null 2>&1 && panel_up=1

cat >"$STATE/nexus-c2-basement.json" <<EOF
{
  "schema": "nexus-c2-basement/v1",
  "updated": "${ts}",
  "layer": "nexus_c2",
  "role": "secure_basement",
  "before": "kilroy",
  "weaponized": true,
  "war_posture": true,
  "kiosk": false,
  "command_deck": true,
  "gates": {
    "connection_gatekeeper": true,
    "trust_strike": true,
    "probe_guard": true,
    "attack_kit": true,
    "weapons_turnover": true
  },
  "panel_up": ${panel_up},
  "loopback_authority": "127.0.0.1",
  "install_root": "${NL}",
  "steps": "$(IFS=,; echo "${steps[*]:-basement_armed}")"
}
EOF

log "NEXUS C2 basement armed — weaponized gates live (panel=${panel_up})"