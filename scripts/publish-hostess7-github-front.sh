#!/usr/bin/env bash
# Publish Hostess7 GitHub front page — README.md + LICENSE (All Rights Reserved)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
README="${ROOT}/README-HOSTESS7.md"
LICENSE="${ROOT}/LICENSE-HOSTESS7"
STAGE="${ROOT}/dist/hostess7-github-front"
REMOTE="https://github.com/ZacharyGeurts/Hostess7.git"

[[ -f "$README" ]] || { echo "missing README-HOSTESS7.md" >&2; exit 1; }
[[ -f "$LICENSE" ]] || { echo "missing LICENSE-HOSTESS7" >&2; exit 1; }

rm -rf "$STAGE"
mkdir -p "$STAGE"
cp "$README" "$STAGE/README.md"
cp "$LICENSE" "$STAGE/LICENSE"

cd "$STAGE"
if [[ ! -d .git ]]; then
  git init -b main
  git config user.email "gzac5314@users.noreply.github.com"
  git config user.name "ZacharyGeurts"
fi

git add README.md LICENSE
git commit -m "Hostess 7 — README + All Rights Reserved license" || true

if ! gh repo view ZacharyGeurts/Hostess7 >/dev/null 2>&1; then
  gh repo create Hostess7 --public \
    --description "Hostess 7 beta — brain hub + AmmoOS + Grok16 + Queen field stack" \
    --homepage "https://zacharygeurts.github.io/Hostess7/"
fi

git remote remove origin 2>/dev/null || true
git remote add origin "$REMOTE"
git push -u origin main --force

echo "published → https://github.com/ZacharyGeurts/Hostess7"