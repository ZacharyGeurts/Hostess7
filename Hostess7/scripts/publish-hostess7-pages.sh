#!/usr/bin/env bash
# Build full Hostess7 package for GitHub Pages → gh-pages branch.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_SRC="${ROOT}/docs"
PAGES_REPO="${PAGES_REPO:-${ROOT}/.pages-hostess7-publish}"
PAGES_REMOTE="${PAGES_REMOTE:-git@github.com:ZacharyGeurts/Hostess7.git}"
PAGES_BRANCH="${PAGES_BRANCH:-gh-pages}"
# shellcheck source=hostess7-version.sh
source "$ROOT/scripts/hostess7-version.sh"
OWNER="${GITHUB_PAGES_OWNER:-ZacharyGeurts}"
PY=python3

log() { printf '[hostess7-pages] %s\n' "$*"; }

export HOSTESS7_ROOT="$ROOT"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-${ROOT}/..}"
export SG_ROOT="${SG_ROOT:-$(cd "${NEXUS_INSTALL_ROOT}/.." && pwd)}"
export HOSTESS7_LICENSE_MODE=war
_DESKTOP_BRAIN="${HOSTESS7_DESKTOP_BRAIN:-$HOME/Desktop/hostess7-brain}"
export HOSTESS7_BRAIN_STATE="${HOSTESS7_BRAIN_STATE:-$_DESKTOP_BRAIN/state}"
export HOSTESS7_FIELDSTORAGE_BRAIN="${HOSTESS7_FIELDSTORAGE_BRAIN:-$_DESKTOP_BRAIN/fieldstorage/brain}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$HOSTESS7_BRAIN_STATE}"

log "build full stack surfaces (Queen + AmmoOS) + brain corpus + API export"
"$PY" "$ROOT/scripts/hostess7_pages_surfaces_build.py"
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

if [[ "${HOSTESS7_PUSH_GH_PAGES:-0}" == "1" ]]; then
  cd "$PAGES_REPO"
  git add -A
  if git diff --cached --quiet; then
    log "gh-pages branch already up to date"
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
    log "pushed gh-pages (legacy lane — opt-in HOSTESS7_PUSH_GH_PAGES=1)"
  fi
else
  log "skipping gh-pages push — primary lane is Actions workflow (pages.yml)"
fi

if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
  log "CI uses Actions artifact deploy (pages.yml) — skipping gh-pages branch push to avoid dual-deploy race"
  log "guard → scripts/hostess7-pages-deploy-guard.py"
  "$PY" "$ROOT/scripts/hostess7-pages-deploy-guard.py"
  exit 0
fi

log "live → https://zacharygeurts.github.io/Hostess7/"