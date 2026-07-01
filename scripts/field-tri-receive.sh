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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/field-tri-receive.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# 3-field GPS compare → pinpoint 83.1 MHz → play to your speakers.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}"
export NEXUS_FIELD_CATCH_MHZ="${NEXUS_FIELD_CATCH_MHZ:-93.1}"
export NEXUS_FIELD_TRI_CONCEPT="${NEXUS_FIELD_TRI_CONCEPT:-1}"

PY="$ROOT/lib/field-tri-receive.py"
ORCH="$ROOT/lib/field-antenna-orchestrator.py"

usage() {
  cat <<EOF
NEXUS 3-field triangulation receive

  field-tri-receive.sh compare     Show 3 fields vs operator GPS
  field-tri-receive.sh pinpoint    Same as compare (pinpoint coords)
  field-tri-receive.sh listen      Pinpoint + field wave tune (93.1 WIMK)
  field-tri-receive.sh cycle       Full antenna cycle + listen

Requires RTL-SDR dongle for OTA audio:
  pythong lib/field-wave-engine.py ensure

Environment:
  NEXUS_STATE_DIR          State dir
  NEXUS_FIELD_CATCH_MHZ    Target MHz (default 93.1 WIMK)
EOF
}

cmd="${1:-listen}"
shift || true

case "$cmd" in
  compare|pinpoint)
    exec pythong "$PY" compare "${NEXUS_FIELD_CATCH_MHZ}"
    ;;
  listen|receive|catch)
    echo "[field-tri] 3-field pinpoint → ${NEXUS_FIELD_CATCH_MHZ} MHz → speakers"
    pythong "$ROOT/lib/field-wave-engine.py" ensure >/dev/null 2>&1 || true
    pythong "$ORCH" listen "{\"freq_mhz\":${NEXUS_FIELD_CATCH_MHZ},\"live_play\":true}"
    ;;
  cycle)
    pythong "$ORCH" cycle
    pythong "$PY" receive "{\"freq_mhz\":${NEXUS_FIELD_CATCH_MHZ}}"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    echo "Unknown: $cmd" >&2
    usage >&2
    exit 1
    ;;
esac