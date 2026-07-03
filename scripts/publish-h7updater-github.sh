#!/usr/bin/env bash
# Publish H7updater → github.com/ZacharyGeurts/H7updater (Pages from /docs).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${ROOT}/H7updater"
CLONE="${ROOT}/.h7updater-publish"
REMOTE="${H7UPDATER_REMOTE:-https://github.com/ZacharyGeurts/H7updater.git}"
VER="${H7UPDATER_VERSION:-1.0.0}"

[[ -d "$SRC" ]] || { echo "Missing ${SRC}" >&2; exit 1; }

echo "=== Rebuild stack index ==="
python3 "${SRC}/scripts/build-stack-index.py"

if ! gh repo view ZacharyGeurts/H7updater >/dev/null 2>&1; then
  echo "Creating ZacharyGeurts/H7updater…"
  gh repo create ZacharyGeurts/H7updater --public \
    --description "Hostess 7 official update catalog — sovereign stack + personal OAuth lane"
fi

if [[ ! -d "${CLONE}/.git" ]]; then
  rm -rf "$CLONE"
  git clone --depth 1 "$REMOTE" "$CLONE" 2>/dev/null || {
    mkdir -p "$CLONE"
    git -C "$CLONE" init -b main
    git -C "$CLONE" remote add origin "$REMOTE"
  }
fi
git -C "$CLONE" remote set-url origin "$REMOTE" 2>/dev/null || \
  git -C "$CLONE" remote add origin "$REMOTE"

git -C "$CLONE" pull --ff-only origin main 2>/dev/null || true

rsync -a --delete \
  --exclude='.git' \
  --exclude='scripts/build-stack-index.py' \
  "${SRC}/" "${CLONE}/"

# Keep build script in repo
mkdir -p "${CLONE}/scripts"
cp "${SRC}/scripts/build-stack-index.py" "${CLONE}/scripts/"

cd "$CLONE"
git add -A
git diff --cached --quiet && { echo "H7updater up to date"; exit 0; }

git -c user.email="gzac5314@users.noreply.github.com" -c user.name="ZacharyGeurts" \
  commit -m "H7updater v${VER} — stack index · OAuth doctrine · Pages UI"

git push -u origin main 2>/dev/null || git push -u origin HEAD

gh api -X POST "repos/ZacharyGeurts/H7updater/pages" \
  -f build_type=legacy \
  -f source[branch]=main \
  -f source[path]=/docs 2>/dev/null \
  || gh api -X PUT "repos/ZacharyGeurts/H7updater/pages" \
  -f build_type=legacy \
  -f source[branch]=main \
  -f source[path]=/docs 2>/dev/null || true

echo "H7updater: https://zacharygeurts.github.io/H7updater/"