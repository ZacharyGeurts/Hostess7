#!/usr/bin/env bash
# Account-wide GitHub hygiene — cut extra branches; document fork policy.
# ALL RIGHTS RESERVED is the terms. No forks · no branches.
set -euo pipefail

OWNER="${GITHUB_ACCOUNT:-ZacharyGeurts}"
KEEP_RE="${GITHUB_KEEP_BRANCHES:-^(main|master|gh-pages)$}"
DRY="${GITHUB_HYGIENE_DRY:-0}"

log() { printf '[github-hygiene] %s\n' "$*"; }

gh_json() {
  gh api "$1" 2>/dev/null || echo "[]"
}

list_owned_repos() {
  python3 - "$OWNER" <<'PY'
import json, subprocess, sys
owner = sys.argv[1]
repos = []
page = 1
while True:
    p = subprocess.run(
        ["gh", "api", f"user/repos?per_page=100&page={page}&affiliation=owner"],
        capture_output=True, text=True, errors="replace",
    )
    if p.returncode != 0:
        break
    batch = json.loads(p.stdout or "[]")
    if not batch:
        break
    for r in batch:
        if r.get("owner", {}).get("login") == owner:
            repos.append(r["name"])
    if len(batch) < 100:
        break
    page += 1
print("\n".join(repos))
PY
}

cut_extra_branches() {
  local repo="$1"
  local branches deleted=0
  branches="$(gh api "repos/${OWNER}/${repo}/branches?per_page=100" --jq '.[].name' 2>/dev/null || true)"
  while IFS= read -r br; do
    [[ -z "$br" ]] && continue
    if [[ "$br" =~ $KEEP_RE ]]; then
      continue
    fi
    if [[ "$DRY" == "1" ]]; then
      log "DRY delete ${repo}:${br}"
      deleted=$((deleted + 1))
      continue
    fi
    if gh api -X DELETE "repos/${OWNER}/${repo}/git/refs/heads/${br}" >/dev/null 2>&1; then
      log "deleted ${repo}:${br}"
      deleted=$((deleted + 1))
    else
      log "WARN failed ${repo}:${br}"
    fi
  done <<< "$branches"
  echo "$deleted"
}

disable_forking() {
  local repo="$1"
  if [[ "$DRY" == "1" ]]; then
    log "DRY disable forking ${repo}"
    return 0
  fi
  if gh api -X PATCH "repos/${OWNER}/${repo}" -f allow_forking=false >/dev/null 2>&1; then
    log "forking disabled ${repo}"
    return 0
  fi
  log "forking lock unavailable ${repo} (personal public repos — terms + LICENSE enforce)"
  return 0
}

delete_owned_forks() {
  local forks
  forks="$(gh api "user/repos?affiliation=owner&per_page=100" --jq '.[] | select(.fork==true) | .full_name' 2>/dev/null || true)"
  while IFS= read -r full; do
    [[ -z "$full" ]] && continue
    if [[ "$DRY" == "1" ]]; then
      log "DRY delete fork ${full}"
      continue
    fi
    gh repo delete "$full" --yes 2>/dev/null && log "deleted fork ${full}" || log "WARN fork delete ${full}"
  done <<< "$forks"
}

main() {
  command -v gh >/dev/null 2>&1 || { log "gh missing"; exit 1; }
  log "ALL RIGHTS RESERVED is the terms — account hygiene for ${OWNER}"
  delete_owned_forks
  local total_del=0
  while IFS= read -r repo; do
    [[ -z "$repo" ]] && continue
    disable_forking "$repo" || true
    n="$(cut_extra_branches "$repo")"
    total_del=$((total_del + n))
  done < <(list_owned_repos)
  log "done — extra branches cut: ${total_del}"
}

case "${1:-run}" in
  run) main ;;
  dry) GITHUB_HYGIENE_DRY=1 main ;;
  status)
    gh api user --jq '{login, type}'
    list_owned_repos | wc -l | xargs -I{} log "owned repos: {}"
    gh api "user/repos?affiliation=owner&per_page=100" --jq '[.[]|select(.fork==true)|.full_name]' 2>/dev/null
    ;;
  -h|--help)
    cat <<EOF
github-account-no-forks-branches.sh — cut branches account-wide; enforce no-fork posture

  run     Delete owned forks + extra branches (keep main/master/gh-pages)
  dry     Print actions only
  status  Quick account summary

Env: GITHUB_ACCOUNT (default ZacharyGeurts), GITHUB_HYGIENE_DRY=1
EOF
    ;;
  *) echo "usage: $0 {run|dry|status}" >&2; exit 1 ;;
esac