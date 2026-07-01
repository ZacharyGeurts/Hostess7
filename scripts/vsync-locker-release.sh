#!/usr/bin/env bash
# VSYNC-Locker full release — Grok16 verify, pack all platforms, publish ZacharyGeurts/VSYNC-Locker.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VER="$(python3 -c "import json;from pathlib import Path;d=json.loads(Path('${ROOT}/data/field-vsync-locker-version.json').read_text());print(d['version'])")"
PUSH=0

for arg in "$@"; do
  case "$arg" in
    --push) PUSH=1 ;;
    -v|--version) VER="${2:-$VER}" ;;
  esac
done

export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
log() { printf '[%s] vsync-release %s\n' "$(date +%H:%M:%S)" "$*"; }

log "Grok16 toolchain verify"
GROK16="${ROOT}/Grok16"
[[ -d "$GROK16" ]] || GROK16="$(cd "${ROOT}/../Grok16" 2>/dev/null && pwd || true)"
if [[ -d "$GROK16" && -f "${GROK16}/scripts/grok16-toolchain.sh" ]]; then
  bash "${GROK16}/scripts/grok16-toolchain.sh" status >/dev/null 2>&1 \
    && log "g16 ready" \
    || log "WARN g16 status partial — pack continues with gcc fallback"
else
  log "WARN Grok16 tree missing — gcc fallback for native stub"
fi

log "VSYNC locker module smoke"
python3 -m py_compile "${ROOT}/lib/field-vsync-locker.py"
python3 "${ROOT}/lib/field-vsync-locker.py" harden >/dev/null

log "pack all platforms"
bash "${ROOT}/scripts/pack-vsync-locker.sh"

if [[ "$PUSH" -eq 0 ]]; then
  log "built at ${ROOT}/dist (pass --push to publish https://github.com/ZacharyGeurts/VSYNC-Locker)"
  exit 0
fi

chmod +x "${ROOT}/scripts/publish-vsync-locker-github.sh"
bash "${ROOT}/scripts/publish-vsync-locker-github.sh" --push -v "$VER"
log "done — https://github.com/ZacharyGeurts/VSYNC-Locker/releases/tag/v${VER}"