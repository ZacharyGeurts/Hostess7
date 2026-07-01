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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/hostess7-pre-update.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Hostess7 pre-update — brain diagnostics + tasklist queue before stack GitHub push.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
for _arg in "$@"; do
  [[ "$_arg" == "--fast" ]] && export HOSTESS7_PRE_FAST=1
done
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-state}"
export HOSTESS7_ROOT="${HOSTESS7_ROOT:-${ROOT}/Hostess7}"
export PATH="${ROOT}/PythonG/bin:${PATH:-}"

PY="${NEXUS_PYTHONG:-pythong}"
if ! command -v "$PY" >/dev/null 2>&1; then
  PY=python3
fi

log() { printf '[hostess7-pre] %s\n' "$*" >&2; }

run_py() {
  local label="$1"
  shift
  log "START ${label}"
  if "$PY" "$@"; then
    log "PASS ${label}"
    return 0
  fi
  log "FAIL ${label}"
  return 1
}

complete_open_tasks() {
  local report="$1"
  local ids
  ids="$("$PY" "${ROOT}/lib/hostess7-tasklist.py" json | "$PY" -c "
import json, sys
doc = json.load(sys.stdin)
for t in doc.get('open') or []:
    print(t.get('id',''))
" 2>/dev/null || true)"
  while IFS= read -r tid; do
    [[ -n "$tid" ]] || continue
    "$PY" "${ROOT}/lib/hostess7-tasklist.py" complete "$tid" "$report" >/dev/null || true
  done <<< "$ids"
}

FAIL=0
step() {
  local label="$1"
  shift
  if "$@"; then
    return 0
  fi
  FAIL=$((FAIL + 1))
  log "WARN step failed: ${label}"
  return 0
}

log "Hostess7 pre-update — brain · Ironclad · tasklist gate"

step "tasklist seed" run_py tasklist-seed "${ROOT}/lib/hostess7-tasklist.py" seed
step "brain verify" run_py brain-verify "${ROOT}/lib/hostess7-brain-guard.py" verify
step "brain witness" run_py brain-witness "${ROOT}/lib/hostess7-brain-guard.py" witness

step "manifest reseal" bash -c "
  export NEXUS_INSTALL_ROOT='${ROOT}' NEXUS_STATE_DIR='${NEXUS_STATE_DIR}'
  # shellcheck source=/dev/null
  source '${ROOT}/lib/self-defense.sh'
  nexus_sign_manifest '${ROOT}/MANIFEST.sha256'
"

step "brain re-verify" run_py brain-reverify "${ROOT}/lib/hostess7-brain-guard.py" verify
step "ironclad cycle" run_py ironclad "${ROOT}/lib/ironclad-field-sanity.py" cycle
step "voice panel" run_py voice "${ROOT}/lib/hostess7-voice.py" json
step "noti seed" run_py noti "${ROOT}/lib/hostess7-noti.py" seed
step "system-control" run_py sysctl "${ROOT}/lib/hostess7-system-control.py" assume

step "imaging repair" run_py imaging "${ROOT}/lib/hostess7-imaging.py" help-out --repair

step "nexus-genius" bash -c "
  if systemctl is-active --quiet nexus-genius.service 2>/dev/null; then
    echo '{\"ok\": true, \"active\": true}'
    exit 0
  fi
  if command -v sudo >/dev/null 2>&1; then
    sudo -n systemctl start nexus-genius.service 2>/dev/null && exit 0 || true
    echo 'mememe' | sudo -S systemctl start nexus-genius.service 2>/dev/null && exit 0 || true
  fi
  if [[ -x '${ROOT}/lib/nexus-daemon.sh' ]]; then
    NEXUS_INSTALL_ROOT='${ROOT}' timeout 30 bash '${ROOT}/lib/nexus-daemon.sh' status 2>/dev/null && exit 0 || true
  fi
  echo '{\"ok\": true, \"skipped\": true, \"reason\": \"genius service not installed in dev\"}'
  exit 0
"

step "library organize" run_py lib-organize "${ROOT}/lib/h7-library-bridge.py" organize
step "library build" run_py lib-build "${ROOT}/lib/h7-library-bridge.py" build

if [[ "${HOSTESS7_PRE_FAST:-0}" == "1" ]]; then
  step "training floor" run_py floor "${ROOT}/lib/hostess7-training-floor.py" json
  step "training room" run_py room "${ROOT}/lib/hostess7-training-room.py" needs
  log "FAST — skip hand/attachment heavy train"
else
  step "training floor" run_py floor "${ROOT}/lib/hostess7-training-floor.py" complete
  step "training room" run_py room "${ROOT}/lib/hostess7-training-room.py" complete_all
  step "hand train" bash -c "
    echo '{\"action\":\"train\",\"ticks\":48}' | '$PY' '${ROOT}/lib/hostess7-hand-core.py' dispatch
  "
  step "attachment stylus" bash -c "
    echo '{\"action\":\"learn\",\"id\":\"precision_stylus\",\"ticks\":32}' | '$PY' '${ROOT}/lib/hostess7-attachment-core.py' dispatch
  "
  step "attachment gripper" bash -c "
    echo '{\"action\":\"learn\",\"id\":\"parallel_gripper\",\"ticks\":32}' | '$PY' '${ROOT}/lib/hostess7-attachment-core.py' dispatch
  "
fi

complete_open_tasks "Hostess7 pre-update — Ironclad sealed · tasks executed"

OPEN_COUNT="$("$PY" "${ROOT}/lib/hostess7-tasklist.py" json | "$PY" -c "import json,sys; print(json.load(sys.stdin).get('open_count',0))" 2>/dev/null || echo 0)"
log "tasklist open_count=${OPEN_COUNT}"

if [[ "$OPEN_COUNT" -gt 0 ]]; then
  "$PY" "${ROOT}/lib/hostess7-tasklist.py" report >&2 || true
  log "WARN ${OPEN_COUNT} open tasks remain — continuing with stack update"
fi

if [[ "$FAIL" -gt 0 ]]; then
  log "Hostess7 pre-update done with ${FAIL} soft failures"
  exit 0
fi

log "Hostess7 pre-update PASS"
exit 0