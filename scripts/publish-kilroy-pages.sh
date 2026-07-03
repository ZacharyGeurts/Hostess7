#!/usr/bin/env bash
# Publish KILROY online test environment → GitHub Pages gh-pages.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KILROY="${KILROY_ROOT:-${ROOT}/KILROY}"
DOCS="${KILROY}/docs"
REMOTE="${KILROY_PAGES_REMOTE:-https://github.com/ZacharyGeurts/KILROY.git}"
PAGES_REPO="${PAGES_REPO:-${ROOT}/.pages-kilroy-publish}"
BRANCH="${PAGES_BRANCH:-gh-pages}"
VER="$(grep -m1 '^KILROY Field OS' "${KILROY}/KILROY_VERSION" 2>/dev/null | awk '{print $4}' || echo 2.0.0)"

log() { printf '[kilroy-pages] %s\n' "$*"; }

[[ -d "$DOCS" ]] || { echo "Missing ${DOCS}" >&2; exit 1; }

if [[ ! -d "${PAGES_REPO}/.git" ]]; then
  rm -rf "$PAGES_REPO"
  if git ls-remote --heads "$REMOTE" "$BRANCH" 2>/dev/null | grep -q "$BRANCH"; then
    git clone --branch "$BRANCH" --single-branch "$REMOTE" "$PAGES_REPO"
  else
    mkdir -p "$PAGES_REPO"
    git -C "$PAGES_REPO" init -b "$BRANCH"
    git -C "$PAGES_REPO" remote add origin "$REMOTE"
  fi
fi

rsync -a --delete \
  --exclude='.git' \
  "${DOCS}/" "${PAGES_REPO}/"

cd "$PAGES_REPO"
git add -A
if git diff --cached --quiet; then
  log "KILROY Pages up to date"
else
  git -c user.email="gzac5314@users.noreply.github.com" -c user.name="ZacharyGeurts" \
    commit -m "pages: KILROY online test env v${VER}"
  git push origin "$BRANCH" 2>/dev/null || git push -u origin "$BRANCH"
  log "pushed ${BRANCH}"
fi

log "live → https://zacharygeurts.github.io/KILROY/"