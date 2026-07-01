# AmmoLang boundary route — AML_BUILD=1 universal boundary
_aml_find_root() {
  local d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  while [[ "$d" != "/" ]]; do
    [[ -f "$d/lib/ammolang-run.sh" ]] && echo "$d" && return 0
    d="$(dirname "$d")"
  done
  return 1
}
if [[ "${AML_BUILD:-1}" != "0" ]] && [[ -z "${AML_BOUNDARY_ACTIVE:-}" ]]; then
  _AML_ROOT="$(_aml_find_root 2>/dev/null || true)"
  if [[ -n "$_AML_ROOT" ]]; then
    export AML_BOUNDARY_ACTIVE=1
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/v10-mission.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# NEXUS-Shield v10 agent mission — sequential phases (safe, non-destructive).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
PHASE=0
log() { echo "[$(date +%T)] PHASE $((PHASE+=1)): $*"; }

log "1. BASELINE — optional perf/py-spy"
"$ROOT/scripts/profile-baseline.sh" || true

log "2. RUST CORE — build when cargo present"
if command -v cargo >/dev/null 2>&1; then
  "$ROOT/scripts/build-rust-core.sh" || true
else
  echo "cargo not installed — skip rust core (apt install rustc cargo)"
fi

log "3. SANDBOX — military_sandbox.sh ready"
test -x "$ROOT/scripts/military_sandbox.sh"

log "4. STORAGE + ENERGY — efficient_store + thermal governor"
NEXUS_STATE_DIR="$NEXUS_STATE_DIR" pythong "$ROOT/lib/efficient_store.py" panel
NEXUS_STATE_DIR="$NEXUS_STATE_DIR" pythong "$ROOT/lib/thermal-governor.py" panel

log "5. TESTS + UNIFY — property tests + field fabric"
pythong "$ROOT/tests/property.py" -v
pythong "$ROOT/lib/field-fabric-bridge.py" panel | head -c 400
echo ""

log "6. GUI — field inspector wired in panel/threat-panel.html"
grep -q field-inspector "$ROOT/panel/threat-panel.html"

log "v10 mission scaffold complete — run ./scripts/reboot-nexus.sh to apply panel"
echo "Version: $(grep NEXUS_VERSION= "$ROOT/lib/nexus-common.sh" | head -1)"
