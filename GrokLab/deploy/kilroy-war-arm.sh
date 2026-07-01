#!/usr/bin/env bash
# KILROY war package — armed defensive perimeter, RE-KILL deploying on world field nodes.
set -euo pipefail

NL="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
SG="${SG_ROOT:-$(cd "$NL/.." && pwd)}"
STATE="${NEXUS_STATE_DIR:-$NL/.nexus-state}"
PY="${GROK_LAB_PY:-python3}"

log() { printf '[kilroy-war] %s\n' "$*"; }

export SG_ROOT="$SG" NEXUS_INSTALL_ROOT="$NL" NEXUS_STATE_DIR="$STATE"
export KILROY_ROOT="${KILROY_ROOT:-$NL/KILROY}"

if [[ -x "$NL/Grok16/bin/gpy-16" ]]; then
  export PATH="$NL/Grok16/bin:$PATH"
  [[ ! -e "$NL/Grok16/bin/pythong" ]] && ln -sf gpy-16 "$NL/Grok16/bin/pythong"
  PY="$NL/Grok16/bin/gpy-16"
fi

[[ -f "$KILROY_ROOT/scripts/build-kilroy.sh" ]] || { log "no KILROY — skip"; exit 0; }

export KILROY_PC_CORE=1 KILROY_WAR_POSTURE=1 KILROY_DEFENSIVE_ONLY=1
export KILROY_WAR_SCOPE=defensive_perimeter KILROY_LOOPBACK_SANCTUARY=1
export NEXUS_BOOT_REKILL=1 NEXUS_EVERY_KILL_REKILL=1 NEXUS_FIELD_ATTACK_KIT=1
mkdir -p "$STATE"

log "=== KILROY war package — arm + deploy ==="

ts=$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u)
panel_up=0
curl -sf http://127.0.0.1:9477/grok-lab >/dev/null 2>&1 && panel_up=1

# Stamp KILROY PC core + defense/offense (userspace graft — no kernel bzImage on QEMU yet)
cat >"$STATE/kilroy-loopback.json" <<EOF
{"schema":"kilroy-loopback/v1","owner":"kilroy_core","loopback_authority":"127.0.0.1","transparent":true,"active":${panel_up},"updated":"${ts}"}
EOF
cat >"$STATE/kilroy-defense-offense.json" <<EOF
{"schema":"kilroy-defense-offense/v1","owner":"kilroy_core","war_scope":"defensive_perimeter","defensive_only":true,"hostile_inside":false,"self_harm_forbidden":true,"attack_kit_present":true,"offense_scope":"reactive_confirmed_threat_only","updated":"${ts}"}
EOF
cat >"$STATE/kilroy-core.json" <<EOF
{"schema":"kilroy-core/v1","updated":"${ts}","role":"pc_core","war_posture":true,"defensive_only":true,"war_scope":"defensive_perimeter","loopback_authority":"127.0.0.1","boot_ready":true,"kilroy_grants_field":true,"nexus_c2":${panel_up},"world_node":true,"install_root":"${NL}"}
EOF
log "kilroy core stamped"

timeout 10 "$PY" "$NL/lib/kilroy-boot-services.py" board >/dev/null 2>&1 || true
timeout 10 "$PY" "$NL/lib/kilroy-field-brain.py" board >/dev/null 2>&1 || true

if [[ -f "$NL/lib/field-attack-kit.py" ]]; then
  export NEXUS_BOOT_REKILL_ONLINE=0
  rekill=$(timeout 25 "$PY" "$NL/lib/field-attack-kit.py" boot-rekill 2>/dev/null || echo '{}')
  count=$(echo "$rekill" | "$PY" -c "import sys,json;d=json.load(sys.stdin);print(d.get('rekill',{}).get('rekilled_count',0))" 2>/dev/null || echo 0)
  log "boot-rekill deploying — rekilled=$count"
fi

# Non-Field-1 → hostile → bring to Field 1
DEPLOY="$(cd "$(dirname "$0")" && pwd)"
if [[ -f "$DEPLOY/field-one-world-bring.sh" ]]; then
  bash "$DEPLOY/field-one-world-bring.sh" 2>&1 | tail -4 || true
fi

cat >"$STATE/kilroy-war-package.json" <<EOF
{"schema":"kilroy-war-package/v1","updated":"${ts}","armed":true,"deploying":true,"war_posture":true,"defensive_only":true,"war_scope":"defensive_perimeter","loopback_authority":"127.0.0.1","kilroy_root":"${KILROY_ROOT}","boot_rekill":true,"every_kill_rekill":true,"world_node":true}
EOF
log "KILROY war package armed"