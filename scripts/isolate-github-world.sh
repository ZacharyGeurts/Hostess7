#!/usr/bin/env bash
# Isolate from hostile GitHub — sovereign primary, world export, mirror optional.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-field-drive/nexus-field/state}"
export NEXUS_HUB_STUBS_ENABLE=0
export NEXUS_GITHUB_ISOLATED=1
export HOSTESS7_PRESUME_HOSTILE=1
export HOSTESS7_GIT_TUNNEL=tunnel
PY="${PYTHON:-python3}"

log() { printf '[isolate-github-world] %s\n' "$*"; }

PUSH_GH=0
for arg in "$@"; do
  case "$arg" in
    --push-github|--mirror-push) PUSH_GH=1 ;;
  esac
done

log "sovereign DNS truth + hostile path harden"
[[ -f "$ROOT/lib/field-dns-resolve.py" ]] && "$PY" "$ROOT/lib/field-dns-resolve.py" ensure >/dev/null 2>&1 || true

log "isolate — field drive + world export (GitHub mirror push=${PUSH_GH})"
if [[ "$PUSH_GH" -eq 1 ]]; then
  export NEXUS_GITHUB_MIRROR_PUSH=1
fi
"$PY" "$ROOT/lib/field-github-isolation.py" isolate | "$PY" -c "
import json,sys
d=json.load(sys.stdin)
w=d.get('world_urls') or {}
print('  isolated:', d.get('isolated'), 'ammonet:', d.get('ammonet_version'))
print('  sovereign:', w.get('sovereign_panel'))
print('  world export:', w.get('world_export'))
print('  github mirror:', w.get('github_pages'), '(degraded)')
"

log "rack provision — one field per box, whole system"
if [[ -f "$ROOT/scripts/field-rack-provision.sh" ]]; then
  FIELD_RACK_ID="${FIELD_RACK_ID:-rack-$(hostname -s 2>/dev/null || echo local)}" \
    bash "$ROOT/scripts/field-rack-provision.sh" 2>/dev/null || log "  WARN rack provision deferred"
fi

log "done — world sees sovereign loopback + field drive; GitHub optional"