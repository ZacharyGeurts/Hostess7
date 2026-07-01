#!/usr/bin/env bash
# Post-install verification — core status + brain/state migration marker
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export HOSTESS7_ROOT="$ROOT"
export HOSTESS7_BRAIN_STATE="${HOSTESS7_BRAIN_STATE:-$ROOT/brain/state}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$HOSTESS7_BRAIN_STATE}"
export HOSTESS7_WAR_PROFILE="${HOSTESS7_WAR_PROFILE:-1}"

PY="${NEXUS_PYTHONG:-$(command -v pythong 2>/dev/null || command -v python3)}"

echo "[verify-embed] hostess7 core status"
"$PY" -m hostess7.core status || hostess7-core status

MIG="${HOSTESS7_BRAIN_STATE}/migration.json"
if [[ -f "$MIG" ]]; then
  echo "[verify-embed] migration marker present: $MIG"
else
  "$PY" -c "from hostess7.paths import brain_state_dir; brain_state_dir()"
  [[ -f "$MIG" ]] || echo "[verify-embed] WARN: migration marker not created"
fi

echo "[verify-embed] cohesion"
HOSTESS7_WAR_PROFILE=1 "$PY" -m hostess7.cohesion all

echo "[verify-embed] war sim"
HOSTESS7_WAR_PROFILE=1 "$PY" -m hostess7.war_realism wargame advanced

echo "[verify-embed] OK"