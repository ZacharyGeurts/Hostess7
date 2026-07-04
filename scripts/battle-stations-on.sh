#!/usr/bin/env bash
# Battle Stations — general quarters everywhere (loopback + Pages build env).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
export HOSTESS7_BATTLE_STATIONS=1
export HOSTESS7_WAR_PROFILE=1
export HOSTESS7_LICENSE_MODE=war
export NEXUS_PRESUME_HOSTILE=1
export NEXUS_WAR_MACHINE=1
export NEXUS_FIELD_IPV4_ARBITRARY=1

log() { printf '[battle-stations] %s\n' "$*"; }

log "ARM — war harden + alert posture + battle stations stamp"
python3 "$ROOT/lib/field-battle-stations.py" on

if [[ -x "$ROOT/Hostess7/Hostess7.sh" ]]; then
  bash "$ROOT/Hostess7/Hostess7.sh" alert-posture on 2>/dev/null || true
fi

log "OK — battle stations ON everywhere"
python3 "$ROOT/lib/field-battle-stations.py" json | python3 -c "
import json,sys
d=json.load(sys.stdin)
print('enabled:', d.get('enabled'), 'posture:', d.get('posture'))
p=d.get('policy') or {}
print('six_tool_wall:', p.get('six_tool_wall'), 'war_machine:', p.get('war_machine'))
"