#!/usr/bin/env bash
# Hostess7 → GitHub via secure git (pinned SSH, MITM-resistant, port-443 tunnel fallback)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${HOSTESS7_VERSION:-1.0.7h}"
TAG="v${VERSION}"
REMOTE="${HOSTESS7_GITHUB_REMOTE:-git@github.com:ZacharyGeurts/Hostess7.git}"
BRANCH="${HOSTESS7_GITHUB_BRANCH:-main}"

log() { printf '[hostess7-secure-git] %s\n' "$*"; }

export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$(cd "$ROOT/.." && pwd)}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${NEXUS_INSTALL_ROOT}/.nexus-state}"
STAGE="${HOSTESS7_SECURE_PUBLISH_DIR:-${NEXUS_INSTALL_ROOT}/dist/hostess7-secure-publish}"
SECURE="${ROOT}/scripts/hostess7_secure_git.py"

log "verify pinned GitHub hosts"
pythong "$SECURE" verify
ROUTE="$(pythong "$SECURE" route | pythong -c 'import json,sys; print(json.load(sys.stdin).get("route","none"))')"
log "route: ${ROUTE} (direct=22, tunnel=443)"

log "stage clean tree → ${STAGE}"
rm -rf "$STAGE"
mkdir -p "$STAGE"
rsync -a --delete \
  --exclude='.git' \
  --exclude='cache' \
  --exclude='zac' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  "${ROOT}/" "${STAGE}/"

git -C "$STAGE" init -b "$BRANCH"
git -C "$STAGE" config user.email "${GIT_USER_EMAIL:-gzac5314@users.noreply.github.com}"
git -C "$STAGE" config user.name "${GIT_USER_NAME:-ZacharyGeurts}"
git -C "$STAGE" add -A
git -C "$STAGE" commit -m "Hostess7 ${VERSION} — war-ready boot · secure git" || true

log "github-brain + pages API export"
pythong "$ROOT/scripts/hostess7_github_brain.py" build
pythong "$ROOT/scripts/hostess7_pages_api_export.py"

log "push ${BRANCH} + ${TAG} via pinned SSH"
pythong "$SECURE" push "$STAGE" --branch "$BRANCH" --remote "$REMOTE" --tag "$TAG" --force

log "pages gh-pages"
HOSTESS7_VERSION="$VERSION" bash "$ROOT/scripts/publish-hostess7-pages.sh"

log "done → https://github.com/ZacharyGeurts/Hostess7"