#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
# Hostess 7 advisory + targets — mechanisms KILL/INTERACT; KILL is terminal.
ADV="${ROOT}/lib/hostess7-advisory-body.py"
TGT="${ROOT}/lib/hostess7-targets.py"
BODY="${ROOT}/lib/hostess7-body-control.py"
[[ -f "$ADV" ]]
[[ -f "$TGT" ]]
[[ -f "$BODY" ]]
grep -Fq 'hostess7-advisory-body-panel' <<<"$panel"
grep -Fq 'advisory_channel' <<<"$panel"
ingest=$("$PY" "$ADV" ingest ear "calm counsel for posture check")
grep -Fq '"ok": true' <<<"$ingest"
aid=$(<<<"$ingest" "$PY" -c "import sys,json; print(json.load(sys.stdin)['advisement']['id'])")
discern=$(printf '%s' "{\"action\":\"discern\",\"advisement_id\":\"$aid\"}" | "$PY" "$ADV" dispatch)
grep -Fq '"ok": true' <<<"$discern"
blocked=$(printf '%s' '{"action":"touch_toes"}' | "$PY" "$BODY" dispatch)
grep -Fq 'body_locked_advisory_only' <<<"$blocked"
cleared=$(printf '%s' "{\"action\":\"touch_toes\",\"advisement_id\":\"$aid\"}" | "$PY" "$BODY" dispatch)
grep -Fq '"ok": true' <<<"$cleared" || grep -Fq 'advisement_cleared' <<<"$cleared"
# INTERACT mechanism — non-terminal, modifiable
interact=$(printf '%s' '{"action":"interact","subject":"counsel probe entity","hostility_score":0.6,"threat_score":0.5}' | "$PY" "$TGT" dispatch)
grep -Fq '"mechanism": "INTERACT"' <<<"$interact"
grep -Fq '"status": "active"' <<<"$interact"
iid=$(<<<"$interact" "$PY" -c "import sys,json; print(json.load(sys.stdin)['target']['id'])")
mod=$(printf '%s' "{\"action\":\"modify\",\"target_id\":\"$iid\",\"updates\":{\"counsel\":\"updated interact counsel\"}}" | "$PY" "$TGT" dispatch)
grep -Fq '"modified": true' <<<"$mod"
# KILL mechanism — terminal, dies, no modifications
uniq="suite-kill-$(date +%s)-$$"
hostile=$(printf '%s' "{\"action\":\"ingest\",\"lane\":\"internet\",\"counsel\":\"active C2 beacon weapon attack kill threat $uniq\"}" | "$PY" "$ADV" dispatch)
grep -Fq '"ok": true' <<<"$hostile"
hid=$(<<<"$hostile" "$PY" -c "import sys,json; print(json.load(sys.stdin)['advisement']['id'])")
promote=$(printf '%s' "{\"action\":\"promote\",\"advisement_id\":\"$hid\"}" | "$PY" "$ADV" dispatch)
grep -Fq '"mechanism": "KILL"' <<<"$promote"
grep -Fq '"mechanism": "KILL"' <<<"$promote"
grep -Fq '"target"' <<<"$promote"
grep -Fq '"status": "dead"' <<<"$promote"
grep -Fq '"no_modifications": true' <<<"$promote"
kid=$(<<<"$promote" "$PY" -c "import sys,json; print(json.load(sys.stdin)['target']['id'])")
block_mod=$(printf '%s' "{\"action\":\"modify\",\"target_id\":\"$kid\",\"updates\":{\"counsel\":\"too late\"}}" | "$PY" "$TGT" dispatch)
grep -Fq 'target_sealed_no_modifications' <<<"$block_mod"
block_revoke=$(printf '%s' "{\"action\":\"revoke\",\"target_id\":\"$kid\"}" | "$PY" "$TGT" dispatch)
grep -Fq 'target_no_returns' <<<"$block_revoke"
targets=$("$PY" "$TGT" status)
grep -Fq 'hostess7-targets-panel' <<<"$targets"
grep -Fq 'kill_means_kill' <<<"$targets"
grep -Fq '"dead_count"' <<<"$targets"
mechs=$("$PY" "$TGT" mechanisms)
grep -Fq '"KILL"' <<<"$mechs"
grep -Fq '"INTERACT"' <<<"$mechs"
grep -Fq '/api/hostess7/advisory' "${ROOT}/lib/threat-panel-http.py"
grep -Fq '/api/hostess7/targets' "${ROOT}/lib/threat-panel-http.py"
