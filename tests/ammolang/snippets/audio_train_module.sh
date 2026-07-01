#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/audio-train.py" ]]
  [[ -f "${ROOT}/data/audio-train-seed.json" ]]
  [[ -f "${ROOT}/lib/audio-train.sh" ]]
  grep -q 'audio_train' "${ROOT}/lib/threat-panel.sh"
  grep -q '/api/audio-train' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'view-audio-train' "${ROOT}/panel/threat-panel.html"
  grep -q 'HOSTESS_VERSION="7"' "${ROOT}/lib/nexus-common.sh"
  grep -q 'NEXUS_VERSION="g16-1.0"' "${ROOT}/lib/nexus-common.sh"
out=$("$PY" "${ROOT}/lib/audio-train.py" build 2>/dev/null || true); grep -q 'audio-train/v1'
out=$("$PY" "${ROOT}/lib/audio-train.py" ingest '{"source_id":"test:spotify","label":"Spotify","kind":"music","sample":{"level_db":-18,"peak_db":-6,"bass_energy":0.4,"treble_energy":0.5,"sample_rate_hz":48000,"latency_ms":20}}' 2>/dev/null || true); grep -q '"ok": true'
at_state="$NEXUS_STATE_DIR/audio-train-test"
  mkdir -p "$at_state"
  for i in 1 2 3 4; do
    NEXUS_STATE_DIR="$at_state" NEXUS_INSTALL_ROOT="$ROOT" \
      aml_py "audio-train.py" ingest '{"source_id":"test:tractive","label":"Tractive Pet","kind":"pet","sample":{"level_db":-90,"peak_db":-40,"bass_energy":0.4,"treble_energy":0.5,"sample_rate_hz":48000,"latency_ms":20}}' >/dev/null
  done
out=$("$PY" "${ROOT}/lib/audio-train.py" ingest '{"source_id":"test:tractive","label":"Tractive Pet","kind":"pet","sample":{"level_db":-90,"peak_db":-40,"bass_energy":0.4,"treble_energy":0.5,"sample_rate_hz":48000,"latency_ms":20}}' 2>/dev/null || true); grep -q '"hostile_intent": true'
