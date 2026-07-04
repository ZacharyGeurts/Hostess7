#!/usr/bin/env bash
# AmmoDrive H7 storage — provision fieldstorage + isolate GitHub world.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-field-drive/nexus-field/state}"
export HOSTESS7_TEAM_FIELD="${HOSTESS7_TEAM_FIELD:-/media/default/HOSTESS7_TEAM1/fieldstorage}"
export HOSTESS7_TEAM_H7_FIELD="${HOSTESS7_TEAM_H7_FIELD:-/media/default/HOSTESS7_TEAM/fieldstorage}"
export FIELD_QUBES_MOUNT="${FIELD_QUBES_MOUNT:-/media/default/FIELD_QUBES}"
PY="${PYTHON:-python3}"

DRY=0
FULL=0
H100=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY=1 ;;
    --full) FULL=1 ;;
    --100x) H100=1; FULL=1 ;;
  esac
done
[[ "$H100" -eq 1 ]] && export ZACHUB_100X=1

log() { printf '[zachub-provision] %s\n' "$*"; }

log "AmmoDrive — Grok and Zac own it now"
log "burn stale clones + fired routes (true source only)"
BURN_ARGS=(burn)
[[ "$DRY" -eq 1 ]] && BURN_ARGS+=(--dry)
"$PY" "$ROOT/lib/field-zachub-fork-guard.py" "${BURN_ARGS[@]}" 2>/dev/null | "$PY" -c "
import json,sys
try:
  d=json.load(sys.stdin)
  print('  burned:', d.get('burned_count'), 'ok:', d.get('ok'))
except Exception:
  print('  burn: skipped')
" || true

log "capacity snapshot"
"$PY" "$ROOT/lib/field-zachub-storage.py" capacity | "$PY" -c "
import json,sys
d=json.load(sys.stdin)
nv=d.get('nvme') or {}
zh=d.get('zachub') or {}
print('  nvme free:', nv.get('free_gb'), 'GB')
print('  zachub reserve:', zh.get('reserve_gb'), 'GB used:', zh.get('used_gb'), 'GB')
"

PROV_ARGS=(provision)
[[ "$DRY" -eq 1 ]] && PROV_ARGS+=(--dry-run)
[[ "$FULL" -eq 1 ]] && PROV_ARGS+=(--full)
[[ "$H100" -eq 1 ]] && PROV_ARGS+=(--100x)

log "provision HOSTESS7_TEAM fieldstorage (dry_run=${DRY} full=${FULL} 100x=${H100})"
"$PY" "$ROOT/lib/field-zachub-storage.py" "${PROV_ARGS[@]}" | "$PY" -c "
import json,sys
d=json.load(sys.stdin)
print('  ok:', d.get('ok'))
print('  truth roots:', len(d.get('zachub_truth_roots') or []))
gt=d.get('github_truth') or {}
print('  github mirror:', gt.get('written_count'), 'artifacts, repos:', gt.get('repo_count'))
sg=d.get('sg_siblings') or {}
print('  sg siblings:', sg.get('synced_count'), 'synced')
"

log "burn stale TEAM field1 QEMU stubs (real stack: GrokLab/deploy)"
BURN_QEMU_ARGS=(burn)
[[ "$DRY" -eq 1 ]] && BURN_QEMU_ARGS+=(--dry-run)
"$PY" "$ROOT/lib/field-zachub-qemu-racks.py" "${BURN_QEMU_ARGS[@]}" 2>/dev/null | "$PY" -c "
import json,sys
try:
  d=json.load(sys.stdin)
  print('  stale qemu burned:', d.get('burned_count'), 'ok:', d.get('ok'))
except Exception:
  print('  stale qemu burn: skipped')
" || true

log "provision GrokLab botnet QEMU racks on deploy/ only — no TEAM drive servers"
QEMU_ARGS=(provision)
[[ "$DRY" -eq 1 ]] && QEMU_ARGS+=(--dry-run)
"$PY" "$ROOT/lib/field-zachub-qemu-racks.py" "${QEMU_ARGS[@]}" | "$PY" -c "
import json,sys
d=json.load(sys.stdin)
print('  ok:', d.get('ok'))
print('  slots:', len(d.get('slots') or []))
obd=d.get('one_big_drive') or {}
print('  one_big_drive_gb:', obd.get('logical_gb'), 'racks:', obd.get('rack_count'))
"

if [[ "$DRY" -eq 0 ]]; then
  log "isolate — sovereign primary, GitHub degraded mirror"
  export NEXUS_GITHUB_ISOLATED=1
  export NEXUS_HUB_STUBS_ENABLE=0
  export HOSTESS7_PRESUME_HOSTILE=1
  "$PY" "$ROOT/lib/field-github-isolation.py" isolate | "$PY" -c "
import json,sys
d=json.load(sys.stdin)
w=d.get('world_urls') or {}
print('  isolated:', d.get('isolated'))
print('  sovereign:', w.get('sovereign_panel'))
print('  world export:', w.get('world_export'))
"
fi

log "done — AmmoDrive storage provision complete"