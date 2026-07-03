#!/usr/bin/env bash
# Publish Final_Eye, Final_Ear, Final_Mouth → GitHub (source only; wiki/Pages deferred).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SG="$(cd "${ROOT}/.." && pwd)"
OWNER="${GITHUB_PAGES_OWNER:-ZacharyGeurts}"
VER="${SENSES_VERSION:-$(cat "${SG}/Final_Eye/VERSION" 2>/dev/null || echo 1.3.1)}"
MSG="${SENSES_PUBLISH_MSG:-Hostess7 Military EOL vision — eyes ear mouth v${VER}}"
H7_SECURE="${ROOT}/Hostess7/scripts/hostess7_secure_git.py"

log() { printf '[senses-publish] %s\n' "$*"; }

_git_push() {
  local dir="$1" branch="$2" remote
  remote="$(git -C "$dir" remote get-url origin 2>/dev/null || echo "")"
  if [[ -f "$H7_SECURE" ]] && [[ "$remote" == *github.com* ]]; then
    python3 "$H7_SECURE" push "$dir" --branch "$branch" --remote "$remote" 2>/dev/null && return 0
  fi
  git -C "$dir" push origin "$branch" 2>/dev/null || git -C "$dir" push -u origin "$branch"
}

publish_local_git() {
  local name="$1" src="$2"
  local branch
  branch="$(git -C "$src" branch --show-current 2>/dev/null || echo main)"
  [[ -n "$branch" ]] || branch="main"
  log "${name} local git @ ${src}"
  if ! git -C "$src" diff --quiet || ! git -C "$src" diff --cached --quiet; then
    log "WARN ${name} has uncommitted changes — commit in ${src} before publish"
    return 1
  fi
  local ahead
  ahead="$(git -C "$src" rev-list --count "origin/${branch}..${branch}" 2>/dev/null || echo 0)"
  if [[ "${ahead}" -eq 0 ]]; then
    log "${name} already up to date (local)"
    return 0
  fi
  _git_push "$src" "$branch" || git -C "$src" push origin "$branch"
  log "pushed ${OWNER}/${name} (local git)"
}

publish_git_repo() {
  local name="$1" src="$2"
  if [[ -d "${src}/.git" ]]; then
    publish_local_git "$name" "$src"
    return 0
  fi
  local remote="git@github.com:${OWNER}/${name}.git"
  local work="${ROOT}/.senses-publish-${name}"
  local branch="main"

  log "${name} ← ${src}"
  gh repo view "${OWNER}/${name}" >/dev/null 2>&1 || {
    log "create ${OWNER}/${name}"
    gh repo create "${OWNER}/${name}" --public --description "Hostess 7 ${name} — Military EOL sense lane"
  }

  rm -rf "$work"
  if git ls-remote --heads "$remote" "$branch" 2>/dev/null | grep -q "$branch"; then
    git clone --branch "$branch" --single-branch "$remote" "$work"
  else
    mkdir -p "$work"
    git -C "$work" init -b "$branch"
    git -C "$work" remote add origin "$remote"
  fi

  rsync -a --delete \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='out/' \
    --exclude='cache/' \
    --exclude='releases/' \
    --exclude='*.img' \
    --exclude='*.tar' \
    --exclude='*.tar.gz' \
    --exclude='*.deb' \
    --exclude='*.zip' \
    --exclude='*.xz' \
    --exclude='amouranth_engine.log' \
    --exclude='*.jsonl' \
    --exclude='stoard/witness' \
    "${src}/" "${work}/"

  git -C "$work" add -A
  if git -C "$work" diff --cached --quiet; then
    log "${name} already up to date"
    return 0
  fi
  git -C "$work" -c user.email="gzac5314@users.noreply.github.com" -c user.name="ZacharyGeurts" \
    commit -m "$MSG"
  _git_push "$work" "$branch"
  log "pushed ${OWNER}/${name}"
}

log "Military EOL senses publish v${VER}"
for sense in Final_Eye Final_Ear Final_Mouth; do
  publish_git_repo "$sense" "${SG}/${sense}" || log "WARN ${sense} publish partial"
done

log "done — wiki/Pages hubs deferred (run publish-ammoos-hub-pages.sh when ready)"
log "  https://github.com/${OWNER}/Final_Eye"
log "  https://github.com/${OWNER}/Final_Ear"
log "  https://github.com/${OWNER}/Final_Mouth"