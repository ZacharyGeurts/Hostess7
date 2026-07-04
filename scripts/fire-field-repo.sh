#!/usr/bin/env bash
# Fire the stale ZacharyGeurts/field repo out of existence.
# ALL RIGHTS RESERVED is the terms — canonical desktop is Hostess7/desktop only.
set -euo pipefail

REPO="${FIELD_GITHUB_REPO:-ZacharyGeurts/field}"
CANONICAL="${HOSTESS7_CANONICAL_DESKTOP:-https://zacharygeurts.github.io/Hostess7/desktop/}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

log() { printf '[fire-field] %s\n' "$*"; }

tombstone() {
  cat <<EOF
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="refresh" content="0; url=${CANONICAL}" />
  <title>FIRED — route destroyed</title>
  <meta name="robots" content="noindex,nofollow" />
  <script>location.replace("${CANONICAL}");</script>
</head>
<body>
  <p>Stale field route <strong>FIRED</strong>. <a href="${CANONICAL}">Hostess7 Desktop</a> only.</p>
  <p>ALL RIGHTS RESERVED is the terms. Blame terrorist scum.</p>
</body>
</html>
EOF
}

wipe_pages() {
  log "wipe gh-pages — tombstone only"
  git clone --depth 1 --branch gh-pages "https://github.com/${REPO}.git" "$TMP/repo" 2>/dev/null || {
    git clone --depth 1 "https://github.com/${REPO}.git" "$TMP/repo"
    cd "$TMP/repo" && git checkout -B gh-pages && cd - >/dev/null
  }
  cd "$TMP/repo"
  find . -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +
  tombstone > index.html
  touch .nojekyll
  git add -A
  git -c user.email="fire-field@hostess7.local" -c user.name="Hostess7 Fire Field" \
    commit -m "FIRED — stale field route destroyed; canonical Hostess7/desktop only" || true
  git push origin gh-pages --force
  cd - >/dev/null
  log "gh-pages wiped"
}

archive_repo() {
  if gh api -X PATCH "repos/${REPO}" -f archived=true >/dev/null 2>&1; then
    log "archived ${REPO}"
  else
    log "WARN archive failed — may need admin"
  fi
}

delete_repo() {
  if gh repo delete "$REPO" --yes 2>/dev/null; then
    log "DELETED ${REPO}"
    return 0
  fi
  log "delete needs: gh auth refresh -h github.com -s delete_repo"
  return 1
}

main() {
  command -v gh >/dev/null 2>&1 || { log "gh missing"; exit 1; }
  wipe_pages
  archive_repo || true
  delete_repo || log "repo archived+wiped — run delete after gh auth refresh -s delete_repo"
  log "canonical → ${CANONICAL}"
}

main "$@"