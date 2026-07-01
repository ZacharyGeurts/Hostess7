#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
# Beyond DARPA · Lockheed security — human and machine threats, all systems/data.
BDS="${ROOT}/lib/beyond-darpa-security.py"
IO="${ROOT}/lib/field-io-packet.py"
ADV="${ROOT}/lib/hostess7-advisory-body.py"
[[ -f "$BDS" ]]
grep -Fq 'beyond-darpa-security-panel' <<<"$panel"
grep -Fq 'beyond_darpa_lockheed' <<<"$panel"
grep -Fq 'human_threats_covered' <<<"$panel"
grep -Fq 'machine_threats_covered' <<<"$panel"
grep -Fq '"all_data_secured": true' <<<"$panel"
human=$(printf '%s' '{"action":"assess","channel":"keystroke","text":"credential phishing paste inject"}' | "$PY" "$BDS" dispatch)
grep -Fq 'HUMAN_THREAT' <<<"$human"
machine=$(printf '%s' '{"action":"assess","channel":"internet","text":"C2 beacon malware AsyncRAT exploit"}' | "$PY" "$BDS" dispatch)
grep -Fq 'MACHINE_THREAT' <<<"$machine"
clear=$(printf '%s' '{"action":"assess","channel":"secured","text":"calm posture counsel"}' | "$PY" "$BDS" dispatch)
grep -Fq '"pass_ok": true' <<<"$clear"
grep -Fq '"verdict": "CLEAR"' <<<"$clear"
gate_block=$(printf '%s' '{"action":"gate","channel":"internet","peer":"8.8.8.8","path":"/api/test","body":{"action":"status"}}' | "$PY" "$BDS" dispatch)
grep -Fq 'beyond_darpa_fail_closed' <<<"$gate_block"
grep -Fq 'beyond_darpa_security' "$IO"
grep -Fq 'advisory_for_truth_gate' "$BDS"
grep -Fq '/api/beyond-darpa-security' "${ROOT}/lib/threat-panel-http.py"
grep -Fq '_beyond_darpa_api_gate' "${ROOT}/lib/threat-panel-http.py"
ingest=$(printf '%s' '{"action":"ingest","lane":"ear","counsel":"secured ear counsel"}' | "$PY" "$ADV" dispatch)
grep -Fq 'beyond_darpa_security' <<<"$ingest"
grep -Fq 'beyond_darpa_lockheed' <<<"$ingest"
