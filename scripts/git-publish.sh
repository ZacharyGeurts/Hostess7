# AmmoLang boundary route — AML_BUILD=1 universal boundary
_aml_find_root() {
  local d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  while [[ "$d" != "/" ]]; do
    [[ -f "$d/lib/ammolang-run.sh" ]] && echo "$d" && return 0
    d="$(dirname "$d")"
  done
  return 1
}
if [[ "${AML_BUILD:-1}" != "0" ]] && [[ -z "${AML_BOUNDARY_ACTIVE:-}" ]]; then
  _AML_ROOT="$(_aml_find_root 2>/dev/null || true)"
  if [[ -n "$_AML_ROOT" ]]; then
    export AML_BOUNDARY_ACTIVE=1
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/git-publish.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Normal git publish — commit and push from the live tree (no export clone, no MCP push lane).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SG="$(cd "${ROOT}/.." && pwd)"
VER="${AMMOOS_VERSION:-$(git -C "$ROOT" describe --tags --always 2>/dev/null || echo dev)}"
MSG="${GIT_PUBLISH_MSG:-AmmoOS ${VER} — field stack update}"
WITH_SIBLINGS=0
DRY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --siblings|--all) WITH_SIBLINGS=1; shift ;;
    --dry) DRY=1; shift ;;
    -m|--message) MSG="${2:-$MSG}"; shift 2 ;;
    -h|--help)
      echo "Usage: git-publish.sh [--siblings] [--dry] [-m message]"
      exit 0
      ;;
    *) MSG="$1"; shift ;;
  esac
done

export NEXUS_INSTALL_ROOT="${ROOT}"
export SG_ROOT="${SG}"

log() { printf '[git-publish] %s\n' "$*"; }

git_publish_dir() {
  local dir="$1"
  local message="$2"
  [[ -d "${dir}/.git" ]] || return 0
  local branch
  branch="$(git -C "$dir" branch --show-current 2>/dev/null || echo main)"
  [[ -n "$branch" ]] || branch="main"
  if git -C "$dir" diff --quiet && git -C "$dir" diff --cached --quiet; then
    log "clean ${dir} — push only"
    if [[ "$DRY" -eq 1 ]]; then
      log "dry-run: would push ${dir} (${branch})"
      return 0
    fi
    git -C "$dir" push origin "$branch" 2>/dev/null \
      || git -C "$dir" push -u origin "$branch" \
      || log "WARN push failed ${dir}" >&2
    return 0
  fi
  log "commit ${dir}"
  if [[ "$DRY" -eq 1 ]]; then
    log "dry-run: would commit+push ${dir}: ${message}"
    return 0
  fi
  git -C "$dir" add -A
  git -C "$dir" -c user.email="${GIT_USER_EMAIL:-gzac5314@users.noreply.github.com}" \
    -c user.name="${GIT_USER_NAME:-ZacharyGeurts}" \
    commit -m "$message" || true
  git -C "$dir" push origin "$branch" 2>/dev/null \
    || git -C "$dir" push -u origin "$branch" \
    || log "WARN push failed ${dir}" >&2
}

log "AmmoOS (NewLatest) → origin"
git_publish_dir "$ROOT" "$MSG"

if [[ "$WITH_SIBLINGS" -eq 1 ]]; then
  log "stack siblings"
  for name in Grok16 KILROY AmmoCode Field_Primer Field_Research Final_Eye World_Redata ZNetwork Kill-Grok-Orphans Hostess7; do
    target="${ROOT}/${name}"
    [[ -L "$target" ]] && target="$(readlink -f "$target" 2>/dev/null || readlink "$target")"
    [[ -d "$target" ]] || continue
    git_publish_dir "$target" "${name} — ${MSG}"
  done
  [[ -d "${ROOT}/profile/queen-publish/.git" ]] && git_publish_dir "${ROOT}/profile/queen-publish" "Queen — ${MSG}"
fi

log "done — use: git -C ${ROOT} log -1 --oneline"