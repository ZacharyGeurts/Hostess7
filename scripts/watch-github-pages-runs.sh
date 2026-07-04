#!/usr/bin/env bash
# Watch Hostess7 Pages workflow — cancel runs stuck > STUCK_MIN minutes.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="${HOSTESS7_GITHUB_REPO_SLUG:-ZacharyGeurts/Hostess7}"
WORKFLOW="${PAGES_WORKFLOW:-hostess7-pages.yml}"
STUCK_MIN="${PAGES_STUCK_MIN:-18}"
POLL_SEC="${PAGES_POLL_SEC:-60}"
MAX_ROUNDS="${PAGES_MAX_ROUNDS:-30}"

log() { printf '[pages-watch] %s\n' "$*"; }

cancel_stuck() {
  gh run list --workflow="$WORKFLOW" --repo "$REPO" \
    --json databaseId,status,createdAt,displayTitle --limit 15 2>/dev/null | python3 -c "
import json,sys,subprocess
from datetime import datetime,timezone
stuck=int('${STUCK_MIN}')
runs=json.load(sys.stdin)
now=datetime.now(timezone.utc)
for r in runs:
    st=r.get('status','')
    if st not in ('in_progress','queued','waiting'):
        continue
    created=datetime.fromisoformat(r['createdAt'].replace('Z','+00:00'))
    age=(now-created).total_seconds()/60
    rid=r['databaseId']
    title=(r.get('displayTitle') or '')[:60]
    if age>=stuck:
        subprocess.run(['gh','run','cancel',str(rid),'--repo','${REPO}'],capture_output=True)
        print(f'CANCEL {rid} age={age:.0f}m {title}')
    else:
        print(f'OK    {rid} {st} age={age:.0f}m')
"
}

log "watch ${REPO} workflow ${WORKFLOW} — stuck>${STUCK_MIN}m poll=${POLL_SEC}s"
for ((i=1; i<=MAX_ROUNDS; i++)); do
  log "round ${i}/${MAX_ROUNDS}"
  cancel_stuck || true
  pending="$(gh run list --workflow="$WORKFLOW" --repo "$REPO" --limit 3 --json status,conclusion --jq '[.[]|select(.status==\"completed\" and .conclusion==\"success\")][0].conclusion' 2>/dev/null || true)"
  active="$(gh run list --workflow="$WORKFLOW" --repo "$REPO" --limit 1 --json status,conclusion,url --jq '.[0]|\"\(.status) \(.conclusion//\"\") \(.url)\""' 2>/dev/null || true)"
  log "latest: ${active}"
  if echo "$active" | grep -q 'completed success'; then
    log "Pages deploy success"
    curl -sf --connect-timeout 10 "https://zacharygeurts.github.io/Hostess7/assets/dns-dashboard.js" 2>/dev/null | python3 -c "
import sys
t=sys.stdin.read()
print('live dhcpIsLive:', 'dhcpIsLive' in t, 'bytes:', len(t))
" || true
    exit 0
  fi
  sleep "$POLL_SEC"
done
log "watch ended — check https://github.com/${REPO}/actions"
exit 1