#!/usr/bin/env bash
# Watch Hostess7 Pages workflow — cancel-in-progress is false; queue script clears stuck runs.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
POLL_SEC="${PAGES_POLL_SEC:-60}"
MAX_ROUNDS="${PAGES_MAX_ROUNDS:-30}"

log() { printf '[pages-watch] %s\n' "$*"; }

log "watch ${HOSTESS7_GITHUB_REPO_SLUG:-ZacharyGeurts/Hostess7} — cancel-in-progress false, queue clears stuck"
for ((i=1; i<=MAX_ROUNDS; i++)); do
  log "round ${i}/${MAX_ROUNDS}"
  bash "${ROOT}/scripts/github-pages-queue.sh" cancel-stuck || true
  latest="$(gh run list --workflow="${PAGES_WORKFLOW:-hostess7-pages.yml}" \
    --repo "${HOSTESS7_GITHUB_REPO_SLUG:-ZacharyGeurts/Hostess7}" \
    --limit 1 --json status,conclusion,url,displayTitle \
    --jq '.[0] | "\(.status) \(.conclusion // "") \(.displayTitle // "") \(.url)"' 2>/dev/null || true)"
  log "latest: ${latest}"
  if echo "$latest" | grep -q '^completed success'; then
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
log "watch ended — check https://github.com/${HOSTESS7_GITHUB_REPO_SLUG:-ZacharyGeurts/Hostess7}/actions"
exit 1