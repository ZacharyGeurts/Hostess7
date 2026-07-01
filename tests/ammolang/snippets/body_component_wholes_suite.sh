#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
# Body component wholes — last-known map, eye maintenance, truth-gate advisory.
WHOLES="${ROOT}/lib/field-body-component-wholes.py"
MAINT="${ROOT}/lib/final-eye-maintenance.py"
IO="${ROOT}/lib/field-io-packet.py"
[[ -f "$WHOLES" ]]
[[ -f "$MAINT" ]]
grep -Fq 'field-body-component-panel' <<<"$panel"
grep -Fq '"whole": true' <<<"$panel"
grep -Fq '"id": "hostess7"' <<<"$panel"
grep -Fq '"priority": 1' <<<"$panel"
grep -Fq '"id": "eye"' <<<"$panel"
grep -Fq '"id": "nav"' <<<"$panel"
msg=$("$PY" "${ROOT}/lib/hostess7-self-maintenance.py" message)
grep -Fq 'Maintain yourself Priority 1' <<<"$msg"
grep -Fq '"priority": 1' <<<"$msg"
grep -Fq 'advisory_only' <<<"$panel"
maint=$("$PY" "$MAINT" status)
grep -Fq 'final-eye-maintenance-panel' <<<"$maint"
grep -Fq 'lens_wipe' <<<"$maint"
"$PY" "$MAINT" record lens_wipe "suite test" >/dev/null
after=$("$PY" "$MAINT" status)
grep -Fq 'lens_wipe' <<<"$after"
grep -Fq 'advisory_for_truth_gate' "$IO"
grep -Fq 'advisory_never_defeats_gate' "$IO"
