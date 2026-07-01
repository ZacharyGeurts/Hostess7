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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/digie-minute-check.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Digie minute check — poll stack/tests every 60s, write USER-facing status each tick.
set -euo pipefail
ROOT="${NEXUS_INSTALL_ROOT:-/home/default/Desktop/SG/NewLatest}"
LOG="/tmp/digie-check.log"
UPDATE="/tmp/digie-minute-update.txt"
HISTORY="/tmp/digie-minute-history.log"
INTERVAL="${DIGIE_INTERVAL_SEC:-60}"

cd "$ROOT"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"

ts() { date -u '+%Y-%m-%d %H:%M:%SZ'; }

summarize_json() {
  local label="$1" path="$2"
  if [[ ! -s "$path" ]]; then
    echo "$label: (waiting — no results yet)"
    return
  fi
  timeout 8 python3 - "$label" "$path" <<'PY' 2>/dev/null || echo "$label: (summarize timeout)"
import json, sys
label, path = sys.argv[1], sys.argv[2]
try:
    d = json.load(open(path))
except Exception as e:
    print(f"{label}: unreadable ({e})")
    raise SystemExit(0)
parts = []
for k in ("ok", "suite", "passed", "failed", "total", "stalled", "updated"):
    if k in d:
        parts.append(f"{k}={d[k]}")
print(f"{label}: " + " ".join(parts))
fails = [r for r in (d.get("results") or []) if not r.get("ok")]
if fails:
    print(f"{label} failures ({len(fails)}):")
    for r in fails[:6]:
        print(f"  • {r.get('name','?')[:72]} — {r.get('detail','')}")
PY
}

write_user_update() {
  local block
  block="$(cat <<EOF
=== Digie minute update · $(ts) ===

STACK
$(summarize_json "stack" "/tmp/stack-beta4.json")

PANEL (latest suite)
$(summarize_json "panel" "$NEXUS_STATE_DIR/ammolang-test-panel.json")

COMBINATORICS (last full run)
$(summarize_json "combinatorics" "/tmp/comb-out.json")

PROCESSES
$(timeout 3 ps aux 2>/dev/null | grep -E 'field-ammolang-test\.py' | grep -v grep | head -5 | awk '{print "  pid "$2" · "$11" "$12" "$13}' || echo "  (no ammolang runners)")

RECENT WORK
  • Exploring Vehicles + Exploring Military Vehicles — written to library/dewey/629-vehicles + 355-military-science
  • book-manifest.json + PDF textbooks on both shelves
  • Generator: FIELD_SKIP_COVER=1 (cover render was hanging)

Next check in ${INTERVAL}s.
EOF
)"
  printf '%s\n' "$block" | tee "$UPDATE" >>"$HISTORY"
  echo "[$(ts)] user update written" >>"$LOG"
}

echo "[$(ts)] digie minute check started (interval=${INTERVAL}s, user update → $UPDATE)" >>"$LOG"
while true; do
  write_user_update
  sleep "$INTERVAL"
done