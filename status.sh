#!/usr/bin/env bash
# Stack health — ports, AML tasks, manifest, key doctrine JSON (loopback, no push).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"

PANEL_PORT="${NEXUS_THREAT_PANEL_PORT:-9477}"
QUEEN_PORT="${QUEEN_BROWSER_PORT:-9481}"
WEB_PORT="${HOSTESS7_WEB_PORT:-8080}"
JSON="${1:-}"

_ping() {
  local url="$1"
  if curl -fsS --max-time 3 "$url" >/dev/null 2>&1; then
    echo "up"
  else
    echo "down"
  fi
}

_aml_task() {
  local task="$1"
  if python3 "$ROOT/lib/field-ammolang-build.py" tasks 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert '${task}' in d.get('tasks',{}), d
" 2>/dev/null; then
    echo "ok"
  else
    echo "missing"
  fi
}

_manifest() {
  if [[ -f "$ROOT/MANIFEST.sha256" ]]; then
    awk 'NF>=2 {c++} END{print (c>0)?"present":"empty"}' "$ROOT/MANIFEST.sha256"
  else
    echo "missing"
  fi
}

_verify() {
  if NEXUS_INSTALL_ROOT="$ROOT" ./bin/nexus verify >/dev/null 2>&1; then
    echo "ok"
  else
    echo "fail_or_dev_skip"
  fi
}

_ammo_health() {
  if python3 "$ROOT/lib/ammo-net-health.py" json 2>/dev/null | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d.get('schema')=='ammo-net-health/v1'
" 2>/dev/null; then
    echo "ok"
  else
    echo "missing"
  fi
}

panel=$(_ping "http://127.0.0.1:${PANEL_PORT}/field")
queen=$(_ping "http://127.0.0.1:${QUEEN_PORT}/api/status")
training=$(_ping "http://127.0.0.1:9488/")
web=$(_ping "http://127.0.0.1:${WEB_PORT}/api/status")
aml_boot=$(_aml_task "field_vm_boot")
manifest=$(_manifest)
verify=$(_verify)
ammo_health=$(_ammo_health)

ok=0
[[ "$panel" == "up" ]] || ok=1
[[ "$aml_boot" == "ok" ]] || ok=1

if [[ "$JSON" == "--json" || "$JSON" == "json" ]]; then
  python3 - <<PY
import json
print(json.dumps({
  "schema": "hostess7-stack-status/v1",
  "ok": ${ok} == 0,
  "ports": {
    "panel_${PANEL_PORT}": "${panel}",
    "queen_${QUEEN_PORT}": "${queen}",
    "training_9488": "${training}",
    "hostess7_web_${WEB_PORT}": "${web}",
  },
  "aml": {"field_vm_boot": "${aml_boot}"},
  "manifest": "${manifest}",
  "nexus_verify": "${verify}",
  "ammo_net_health": "${ammo_health}",
  "state_dir": "${NEXUS_STATE_DIR}",
}, indent=2))
PY
  exit "$ok"
fi

cat <<EOF
=== Hostess7 stack status ===
  panel :${PANEL_PORT}     ${panel}
  queen :${QUEEN_PORT}     ${queen}
  training :9488   ${training}
  hostess7 web :${WEB_PORT}  ${web}
  AML field_vm_boot  ${aml_boot}
  MANIFEST.sha256    ${manifest}
  nexus verify       ${verify}
  ammo net health    ${ammo_health}
  state              ${NEXUS_STATE_DIR}
EOF
exit "$ok"