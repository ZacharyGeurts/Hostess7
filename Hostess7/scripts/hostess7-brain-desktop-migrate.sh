#!/usr/bin/env bash
# Move sovereign brain out of SG tree → ~/Desktop/hostess7-brain (GitHub brain stays on Pages).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NL="${NEXUS_INSTALL_ROOT:-$(cd "$ROOT/.." && pwd)}"
DESKTOP="${HOSTESS7_DESKTOP_BRAIN:-$HOME/Desktop/hostess7-brain}"
STATE_DST="$DESKTOP/state"
FS_DST="$DESKTOP/fieldstorage/brain"

log() { printf '[brain-desktop] %s\n' "$*"; }

mkdir -p "$STATE_DST/snapshots" "$FS_DST"

migrate_tree() {
  local src="$1" dst="$2" label="$2"
  [[ -d "$src" ]] || return 0
  local src_real dst_real
  src_real="$(readlink -f "$src" 2>/dev/null || echo "$src")"
  dst_real="$(readlink -f "$dst" 2>/dev/null || echo "$dst")"
  [[ "$src_real" == "$dst_real" ]] && return 0
  log "rsync $label"
  rsync -a --ignore-existing "$src/" "$dst/"
}

migrate_tree "$ROOT/brain/state" "$STATE_DST" "brain/state"
migrate_tree "$ROOT/cache/fieldstorage/brain" "$FS_DST" "fieldstorage/brain"
migrate_tree "$NL/.nexus-state" "$STATE_DST/nexus-state-mirror" "nexus-state snapshot" 2>/dev/null || true

cat > "$DESKTOP/README.txt" <<EOF
Hostess7 sovereign brain — operator desktop storage
GitHub public brain: https://zacharygeurts.github.io/Hostess7/github-brain/corpus.json
Loopback env: export HOSTESS7_BRAIN_STATE=$STATE_DST
EOF

log "sovereign brain → $DESKTOP"
log "set HOSTESS7_BRAIN_STATE=$STATE_DST in shell or Hostess7.sh"