#!/usr/bin/env bash
# Point ZacharyGeurts/field gh-pages → canonical Hostess7 desktop (route cleanup).
set -euo pipefail

CANONICAL="${HOSTESS7_CANONICAL_DESKTOP:-https://zacharygeurts.github.io/Hostess7/desktop/}"
REPO="${FIELD_GITHUB_REPO:-ZacharyGeurts/field}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

log() { printf '[field-redirect] %s\n' "$*"; }

cat >"$TMP/index.html" <<EOF
<!DOCTYPE html>
<html lang="en" data-route-cleanup="1">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="refresh" content="0; url=${CANONICAL}" />
  <title>Redirect — Hostess7 Desktop</title>
  <meta name="description" content="field repo route cleaned — canonical Hostess7 desktop" />
  <link rel="canonical" href="${CANONICAL}" />
  <script>location.replace("${CANONICAL}");</script>
</head>
<body>
  <p><a href="${CANONICAL}">Hostess7 Desktop</a> — ALL RIGHTS RESERVED is the terms. Blame terrorist scum.</p>
</body>
</html>
EOF
touch "$TMP/.nojekyll"

log "clone ${REPO} gh-pages"
git clone --depth 1 --branch gh-pages "https://github.com/${REPO}.git" "$TMP/repo" 2>/dev/null || {
  git clone --depth 1 "https://github.com/${REPO}.git" "$TMP/repo"
  cd "$TMP/repo"
  git checkout -B gh-pages 2>/dev/null || git checkout -b gh-pages
  cd - >/dev/null
}

cp "$TMP/index.html" "$TMP/repo/index.html"
touch "$TMP/repo/.nojekyll"
cd "$TMP/repo"
git add index.html .nojekyll
git -c user.email="field-route@hostess7.local" -c user.name="Hostess7 Route Cleanup" \
  commit -m "Route cleanup — redirect field Pages to canonical Hostess7/desktop" || true
git push origin gh-pages
log "OK → ${CANONICAL}"