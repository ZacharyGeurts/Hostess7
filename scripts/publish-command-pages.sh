#!/usr/bin/env bash
# Publish NEXUS C2 secure basement → https://zacharygeurts.github.io/command/
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
H7="${ROOT}/Hostess7"
STAGE="${H7}/.pages-command-publish"
PAGES_REPO="${PAGES_REPO:-${ROOT}/.pages-command-repo}"
PAGES_REMOTE="${PAGES_REMOTE:-git@github.com:ZacharyGeurts/command.git}"
PAGES_BRANCH="${PAGES_BRANCH:-gh-pages}"
OWNER="${GITHUB_PAGES_OWNER:-ZacharyGeurts}"
PY=python3
H7_SECURE="${H7}/scripts/hostess7_secure_git.py"

log() { printf '[command-pages] %s\n' "$*"; }

export HOSTESS7_ROOT="$H7"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-${ROOT}}"
export HOSTESS7_LICENSE_MODE=war

log "build command basement staging"
"$PY" "${H7}/scripts/hostess7_pages_surfaces_build.py" >/dev/null

[[ -d "$STAGE" && -f "${STAGE}/index.html" ]] || {
  echo "Missing ${STAGE}/index.html — run surfaces build first" >&2
  exit 1
}

log "stage → ${PAGES_REPO} (${PAGES_BRANCH})"
if [[ ! -d "${PAGES_REPO}/.git" ]]; then
  rm -rf "$PAGES_REPO"
  if [[ -f "$H7_SECURE" ]]; then
    "$PY" "$H7_SECURE" verify 2>/dev/null || true
    if ! "$PY" "$H7_SECURE" clone "$PAGES_REPO" --remote "$PAGES_REMOTE" --branch "$PAGES_BRANCH" 2>/dev/null; then
      mkdir -p "$PAGES_REPO"
      git -C "$PAGES_REPO" init -b "$PAGES_BRANCH"
      git -C "$PAGES_REPO" remote add origin "$PAGES_REMOTE" 2>/dev/null || \
        git -C "$PAGES_REPO" remote set-url origin "$PAGES_REMOTE"
    fi
  else
    mkdir -p "$PAGES_REPO"
    git -C "$PAGES_REPO" init -b "$PAGES_BRANCH"
    git -C "$PAGES_REPO" remote add origin "$PAGES_REMOTE" 2>/dev/null || \
      git -C "$PAGES_REPO" remote set-url origin "$PAGES_REMOTE"
  fi
fi

rsync -a --delete --exclude='.git' "${STAGE}/" "${PAGES_REPO}/"

cd "$PAGES_REPO"
git add -A
if git diff --cached --quiet; then
  log "command Pages already up to date"
else
  git -c user.email="gzac5314@users.noreply.github.com" -c user.name="ZacharyGeurts" \
    commit -m "pages: NEXUS C2 secure basement — black emerald rose"
  if [[ -n "${GITHUB_ACTIONS:-}" && -n "${GITHUB_TOKEN:-}" ]]; then
    git remote set-url origin "https://x-access-token:${GITHUB_TOKEN}@github.com/${OWNER}/command.git"
    git push origin "$PAGES_BRANCH" --force
  elif [[ -f "$H7_SECURE" ]]; then
    "$PY" "$H7_SECURE" push "$PAGES_REPO" --branch "$PAGES_BRANCH" \
      --remote "$PAGES_REMOTE" --force
  else
    git push origin "$PAGES_BRANCH" 2>/dev/null || git push -u origin "$PAGES_BRANCH" --force
  fi
  log "pushed gh-pages"
fi

log "live → https://zacharygeurts.github.io/command/"