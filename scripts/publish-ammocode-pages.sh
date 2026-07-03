#!/usr/bin/env bash
# Publish AmmoCode editor → GitHub Pages (static editor, no redirect hub).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${ROOT}/AmmoCode"
REMOTE="${AMMOCODE_PAGES_REMOTE:-https://github.com/ZacharyGeurts/AmmoCode.git}"
PAGES_REPO="${PAGES_REPO:-${ROOT}/.pages-ammocode-publish}"
BRANCH="${PAGES_BRANCH:-gh-pages}"
VER="$(python3 -c "import json;print(json.load(open('${SRC}/data/ammocode-version.json')).get('version','6.1.0'))" 2>/dev/null || echo 6.1.0)"

log() { printf '[ammocode-pages] %s\n' "$*"; }

[[ -d "$SRC" ]] || { echo "Missing ${SRC}" >&2; exit 1; }

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
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='server/' \
  --exclude='ammocode.py' \
  --exclude='.venv' \
  --exclude='node_modules' \
  "${SRC}/" "${PAGES_REPO}/"

cd "$PAGES_REPO"
git add -A
if git diff --cached --quiet; then
  log "AmmoCode Pages up to date"
else
  git -c user.email="gzac5314@users.noreply.github.com" -c user.name="ZacharyGeurts" \
    commit -m "pages: AmmoCode editor v${VER}"
  git push origin "$BRANCH" 2>/dev/null || git push -u origin "$BRANCH"
  log "pushed ${BRANCH}"
fi

log "live → https://zacharygeurts.github.io/AmmoCode/"