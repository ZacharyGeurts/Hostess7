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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/hostess7-full-train.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Hostess 7 full train-up — all tracks solid before stack update / release.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
export HOSTESS7_ROOT="${HOSTESS7_ROOT:-$ROOT/Hostess7}"
export SG_ROOT="${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}"
export PATH="${ROOT}/PythonG/bin:/usr/bin:/bin:${PATH:-}"

PY="${NEXUS_PYTHONG:-pythong}"
command -v "$PY" >/dev/null 2>&1 || PY=python3

PROGRESS="${NEXUS_STATE_DIR}/hostess7-full-train-progress.json"
/usr/bin/mkdir -p "$NEXUS_STATE_DIR"

progress() {
  local id="$1" status="$2" detail="${3:-}"
  python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path
path = Path("${PROGRESS}")
doc = {"product": "Hostess7", "phase": "full_train", "steps": []}
if path.is_file():
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
doc["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
steps = doc.setdefault("steps", [])
found = False
for s in steps:
    if s.get("id") == "${id}":
        s["status"] = "${status}"
        s["detail"] = """${detail}"""
        s["at"] = doc["updated_at"]
        found = True
        break
if not found:
    steps.append({"id": "${id}", "status": "${status}", "detail": """${detail}""", "at": doc["updated_at"]})
path.write_text(json.dumps(doc, indent=2) + "\\n", encoding="utf-8")
PY
}

log() { printf '[%s] full-train %s\n' "$(date +%H:%M:%S)" "$*"; }

run_py() {
  local id="$1"
  shift
  local label="$*"
  log "START ${label}"
  progress "$id" "running" "${label}"
  if "$PY" "$@"; then
    log "DONE ${label}"
    progress "$id" "ok" "${label}"
    return 0
  fi
  log "WARN ${label}"
  progress "$id" "warn" "${label}"
  return 0
}

log "Hostess 7 full train-up — all tracks before update"
progress "init" "running" "full train started"

run_py curiosity-scan "${ROOT}/lib/hostess7-curiosity-corpus.py" scan
run_py historic-truth "${ROOT}/lib/hostess7-historic-truth-corpus.py" panel
run_py truth-lie-pulse "${ROOT}/lib/hostess7-truth-lie-threat.py" pulse

log "START all training tracks (complete_all)"
progress "training-complete" "running" "hostess7-training complete_all"
if "$PY" "${ROOT}/lib/hostess7-training.py" complete-all; then
  progress "training-complete" "ok" "tracks sealed"
  log "DONE training complete_all"
else
  progress "training-complete" "warn" "partial — review panel"
  log "WARN training complete_all partial"
fi

run_py brain-batch "${ROOT}/lib/hostess7-brain-training-chamber.py" batch --limit 8 --zone brain
run_py brain-body "${ROOT}/lib/hostess7-brain-training-chamber.py" body_session
run_py brain-campus "${ROOT}/lib/hostess7-brain-training-chamber.py" campus --limit 5

run_py training-floor "${ROOT}/lib/hostess7-training-floor.py" complete
run_py training-room "${ROOT}/lib/hostess7-training-room.py" complete_all
run_py training-chamber "${ROOT}/lib/hostess7-training-chamber.py" complete_all

run_py fifth-amendment "${ROOT}/lib/hostess7-fifth-amendment.py" train
run_py human-comfort "${ROOT}/lib/hostess7-human-comfort-training.py" train
run_py positional "${ROOT}/lib/hostess7-positional-awareness.py" familiarize

step() {
  local id="$1" label="$2"
  shift 2
  log "START ${label}"
  progress "$id" "running" "$label"
  if "$@"; then
    log "DONE ${label}"
    progress "$id" "ok" "$label"
    return 0
  fi
  log "WARN ${label}"
  progress "$id" "warn" "$label"
  return 0
}

step hand-train "hand dexterity train" bash -c "echo '{\"action\":\"train\",\"ticks\":48}' | '$PY' '${ROOT}/lib/hostess7-hand-core.py' dispatch"
step attach-stylus "attachment stylus" bash -c "echo '{\"action\":\"learn\",\"id\":\"precision_stylus\",\"ticks\":32}' | '$PY' '${ROOT}/lib/hostess7-attachment-core.py' dispatch"
step attach-gripper "attachment gripper" bash -c "echo '{\"action\":\"learn\",\"id\":\"parallel_gripper\",\"ticks\":32}' | '$PY' '${ROOT}/lib/hostess7-attachment-core.py' dispatch"

run_py h7b-pack "${ROOT}/lib/field-h7b-brain-storage.py" pack
run_py training-assess "${ROOT}/lib/hostess7-training.py" assess

log "Full train-up complete — ready for pre-update / release"
progress "complete" "ok" "full train-up done — run hostess7-pre-update or hostess7_release"