#!/usr/bin/env bash
# Publish full AmmoOS + Queen field stack → https://zacharygeurts.github.io/field/
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCS_SRC="${ROOT}/docs"
PAGES_REPO="${PAGES_REPO:-${ROOT}/.pages-field-publish}"
PAGES_REMOTE="${PAGES_REMOTE:-git@github.com:ZacharyGeurts/field.git}"
PAGES_BRANCH="${PAGES_BRANCH:-gh-pages}"
# shellcheck source=hostess7-version.sh
source "$ROOT/scripts/hostess7-version.sh"
FIELD_VERSION="${FIELD_VERSION:-$HOSTESS7_VERSION}"
OWNER="${GITHUB_PAGES_OWNER:-ZacharyGeurts}"
PY="${PYTHONG:-pythong}"
if ! command -v "$PY" >/dev/null 2>&1; then PY=python3; fi

log() { printf '[field-pages] %s\n' "$*"; }

export HOSTESS7_ROOT="$ROOT"
export HOSTESS7_LICENSE_MODE=war
export HOSTESS7_PAGES_BASE="/field"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$(cd "$ROOT/../NewLatest" 2>/dev/null && pwd || echo "$ROOT/../NewLatest")}"

log "build surfaces @ HOSTESS7_PAGES_BASE=${HOSTESS7_PAGES_BASE}"
"$PY" "$ROOT/scripts/hostess7_pages_surfaces_build.py"
"$PY" "$ROOT/scripts/hostess7_pages_brain_build.py" --full
"$PY" "$ROOT/scripts/hostess7_pages_api_export.py"

# threat-panel static stub for command deck shell
mkdir -p "${DOCS_SRC}/api"
if [[ ! -f "${DOCS_SRC}/api/threat-panel.json" ]]; then
  printf '%s\n' '{"ok":true,"pages":true,"posture":"war-ready","gates_held":true,"lane":"pages-surfaces"}' \
    > "${DOCS_SRC}/api/threat-panel.json"
fi

H7_SECURE="${ROOT}/scripts/hostess7_secure_git.py"

if ! gh repo view "${OWNER}/field" --json name >/dev/null 2>&1; then
  log "create GitHub repo ${OWNER}/field"
  gh repo create "${OWNER}/field" --public \
    --description "AmmoOS field desktop — NEXUS C2 · Queen · full panel surfaces on GitHub Pages"
fi

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

rsync -a --delete --exclude='.git' "${DOCS_SRC}/" "${PAGES_REPO}/"

cd "$PAGES_REPO"
git add -A
if git diff --cached --quiet; then
  log "field Pages already up to date"
else
  git -c user.email="gzac5314@users.noreply.github.com" -c user.name="ZacharyGeurts" \
    commit -m "pages: AmmoOS field stack v${FIELD_VERSION}"
  pushed=0
  if [[ -f "$H7_SECURE" ]]; then
    if "$PY" "$H7_SECURE" push "$PAGES_REPO" --branch "$PAGES_BRANCH" \
      --remote "$PAGES_REMOTE" --force 2>/dev/null | grep -q '"ok": true'; then
      pushed=1
    fi
  fi
  if [[ "$pushed" -eq 0 ]]; then
    git push origin "$PAGES_BRANCH" --force 2>/dev/null || git push -u origin "$PAGES_BRANCH" --force
  fi
  log "pushed gh-pages"
fi

gh api -X POST "repos/${OWNER}/field/pages" \
  -f build_type=legacy -f source[branch]=gh-pages -f source[path]=/ 2>/dev/null \
  || gh api -X PUT "repos/${OWNER}/field/pages" \
    -f build_type=legacy -f source[branch]=gh-pages -f source[path]=/ 2>/dev/null \
  || log "configure Pages source gh-pages in repo Settings if needed"

log "live → https://zacharygeurts.github.io/field/"
log "desktop → https://zacharygeurts.github.io/field/desktop/"
log "queen  → https://zacharygeurts.github.io/field/queen/browser.html"