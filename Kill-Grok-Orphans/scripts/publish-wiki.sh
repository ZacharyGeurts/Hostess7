#!/usr/bin/env bash
# Publish wiki/*.md to GitHub wiki repo.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WIKI_SRC="${ROOT}/wiki"
WIKI_REPO="${WIKI_REPO:-${ROOT}/.wiki-publish}"
WIKI_REMOTE="${WIKI_REMOTE:-https://github.com/ZacharyGeurts/Kill-Grok-Orphans.wiki.git}"
VER="$(cat "${ROOT}/VERSION" 2>/dev/null | tr -d '\n' || echo unknown)"

[[ -d "$WIKI_SRC" ]] || { echo "Missing ${WIKI_SRC}" >&2; exit 1; }

if [[ ! -d "${WIKI_REPO}/.git" ]]; then
  rm -rf "$WIKI_REPO"
  git clone "$WIKI_REMOTE" "$WIKI_REPO" 2>/dev/null || {
    mkdir -p "$WIKI_REPO" && cd "$WIKI_REPO" && git init && git remote add origin "$WIKI_REMOTE"
  }
fi

rsync -a --delete --exclude='.git' "${WIKI_SRC}/" "${WIKI_REPO}/"

cd "$WIKI_REPO"
git add -A
git diff --cached --quiet && { echo "Wiki already up to date."; exit 0; }
git -c user.email="gzac5314@users.noreply.github.com" -c user.name="ZacharyGeurts" \
  commit -m "wiki: Kill Grok Orphans ${VER}"
git push origin master 2>/dev/null || git push origin main 2>/dev/null || git push
echo "Wiki published: https://github.com/ZacharyGeurts/Kill-Grok-Orphans/wiki"