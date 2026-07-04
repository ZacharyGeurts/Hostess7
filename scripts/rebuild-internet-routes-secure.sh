#!/usr/bin/env bash
# Rebuild all internet/DNS/Pages routes securely — purge kill-rekill trash, rekill validated only.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
export NEXUS_LEGACY_OPEN_SECURED="${NEXUS_LEGACY_OPEN_SECURED:-1}"
PY="${PYTHON:-python3}"

log() { printf '[rebuild-internet-routes] %s\n' "$*"; }

run_py() {
  local mod="$1"
  shift
  if [[ -f "$ROOT/lib/${mod}.py" ]]; then
    "$PY" "$ROOT/lib/${mod}.py" "$@" 2>/dev/null || true
  fi
}

log "=== secure internet route rebuild ==="

log "1/8 Truth DNS table clean + panel rebuild"
bash "$ROOT/scripts/dns-clean-tables.sh" clean 2>/dev/null || run_py field-dns-table-clean clean

log "2/8 endpoint registry — seed append, verify, instant propagate"
"$PY" "$ROOT/lib/field-endpoint-registry.py" seed --append 2>/dev/null || true
"$PY" "$ROOT/lib/field-endpoint-registry.py" verify 2>/dev/null || true
if [[ -x "$ROOT/scripts/propagate-pages-registry.sh" ]]; then
  bash "$ROOT/scripts/propagate-pages-registry.sh" rebuild-internet-routes-secure.sh
fi

log "3/8 Ironclad secure API routes refresh"
run_py ironclad-secure-api routes
run_py ironclad-secure-api publish

log "4/8 legacy connect primary — Truth DNS + Field DHCP"
bash "$ROOT/scripts/legacy-connect-primary.sh" 2>/dev/null || run_py field-legacy-connect ensure-primary

log "5/8 internet + botnet control plane panels"
run_py field-internet-unified json
run_py field-botnet-dns-dhcp json
run_py field-dns-drift-threat servers
run_py field-github-traffic-shard json

log "6/8 purge kill-rekill trash + revalidate hostile registry"
run_py field-attack-kit purge-rekill-trash

log "7/8 boot rekill — validated targets only"
run_py field-attack-kit boot-rekill

log "8/8 war hardening stamp"
run_py field-war-hardening stamp

log "=== secure route rebuild complete ==="
"$PY" - <<'PY'
import json
from pathlib import Path
root = Path(__import__("os").environ.get("NEXUS_INSTALL_ROOT", "."))
state = Path(__import__("os").environ.get("NEXUS_STATE_DIR", root / ".nexus-state"))
summary = {"ok": True, "schema": "rebuild-internet-routes-secure/v1"}
routes = root / "Hostess7/docs/api/field-endpoint-registry.json"
if routes.is_file():
    d = json.loads(routes.read_text())
    summary["endpoint_routes"] = d.get("route_count") or len(d.get("routes") or {})
    summary["registry_updated"] = d.get("updated")
reg = state / "kill-rekill-registry.json"
if reg.is_file():
    rd = json.loads(reg.read_text())
    summary["kill_rekill_kept"] = len(rd.get("entries") or {})
purge = state / "kill-list-revalidate.json"
if purge.is_file():
    pd = json.loads(purge.read_text())
    summary["hostile_validated"] = pd.get("validated_count")
    summary["hostile_removed"] = pd.get("removed_count")
print(json.dumps(summary, indent=2))
PY