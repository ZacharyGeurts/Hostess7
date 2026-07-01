#!/usr/bin/env bash
# Build full Hostess7 package for GitHub Pages → gh-pages branch.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_SRC="${ROOT}/docs"
PAGES_REPO="${PAGES_REPO:-${ROOT}/.pages-hostess7-publish}"
PAGES_REMOTE="${PAGES_REMOTE:-git@github.com:ZacharyGeurts/Hostess7.git}"
PAGES_BRANCH="${PAGES_BRANCH:-gh-pages}"
HOSTESS7_VERSION="${HOSTESS7_VERSION:-1.0.7h}"
OWNER="${GITHUB_PAGES_OWNER:-ZacharyGeurts}"
PY="${PYTHONG:-pythong}"
if ! command -v "$PY" >/dev/null 2>&1; then PY=python3; fi

log() { printf '[hostess7-pages] %s\n' "$*"; }

export HOSTESS7_ROOT="$ROOT"
export HOSTESS7_LICENSE_MODE=war

log "build full package corpus + API export"
"$PY" "$ROOT/scripts/hostess7_pages_brain_build.py" --full
"$PY" "$ROOT/scripts/hostess7_pages_api_export.py"

H7_SECURE="${ROOT}/scripts/hostess7_secure_git.py"

log "stage docs → ${PAGES_REPO} (${PAGES_BRANCH})"
if [[ ! -d "${PAGES_REPO}/.git" ]]; then
  rm -rf "$PAGES_REPO"
  if [[ -f "$H7_SECURE" ]]; then
    "$PY" "$H7_SECURE" verify
    if ! "$PY" "$H7_SECURE" clone "$PAGES_REPO" --remote "$PAGES_REMOTE" --branch "$PAGES_BRANCH" 2>/dev/null; then
      mkdir -p "$PAGES_REPO"
      git -C "$PAGES_REPO" init -b "$PAGES_BRANCH"
      git -C "$PAGES_REPO" remote add origin "$PAGES_REMOTE"
    fi
  else
    mkdir -p "$PAGES_REPO"
    git -C "$PAGES_REPO" init -b "$PAGES_BRANCH"
    git -C "$PAGES_REPO" remote add origin "$PAGES_REMOTE"
  fi
fi

rsync -a --delete \
  --exclude='.git' \
  "${DOCS_SRC}/" "${PAGES_REPO}/"

cd "$PAGES_REPO"
git add -A
if git diff --cached --quiet; then
  log "GitHub Pages already up to date"
else
  git -c user.email="gzac5314@users.noreply.github.com" -c user.name="ZacharyGeurts" \
    commit -m "pages: Hostess7 full package v${HOSTESS7_VERSION}"
  if [[ -n "${GITHUB_ACTIONS:-}" && -n "${GITHUB_TOKEN:-}" ]]; then
    git remote set-url origin "https://x-access-token:${GITHUB_TOKEN}@github.com/${OWNER}/Hostess7.git"
    git push origin "$PAGES_BRANCH" --force
  elif [[ -f "$H7_SECURE" ]]; then
    "$PY" "$H7_SECURE" push "$PAGES_REPO" --branch "$PAGES_BRANCH" \
      --remote "$PAGES_REMOTE" --force
  else
    git push origin "$PAGES_BRANCH" 2>/dev/null || git push -u origin "$PAGES_BRANCH"
  fi
  log "pushed gh-pages"
fi

log "live → https://zacharygeurts.github.io/Hostess7/"