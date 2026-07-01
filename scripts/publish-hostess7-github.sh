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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/publish-hostess7-github.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Stage full NewLatest → dist/hostess7-github-publish, prune non-set paths, git push Hostess7.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
[[ -f "${ROOT}/lib/nexus-common.sh" ]] && source "${ROOT}/lib/nexus-common.sh"
nexus_release_host_path 2>/dev/null || export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

HOSTESS7_VERSION="${HOSTESS7_VERSION:-1.0.0-beta}"
TAG="v${HOSTESS7_VERSION}"
DIST="${ROOT}/dist"
STAGE="${DIST}/hostess7-github-publish"
REMOTE="${HOSTESS7_GITHUB_REMOTE:-https://github.com/ZacharyGeurts/Hostess7.git}"
PUSH=0
DRY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --push) PUSH=1; shift ;;
    --dry) DRY=1; shift ;;
    -v|--version) HOSTESS7_VERSION="$2"; TAG="v${HOSTESS7_VERSION}"; shift 2 ;;
    -h|--help)
      echo "Usage: publish-hostess7-github.sh [--push] [--dry] [-v VERSION]"
      exit 0
      ;;
    *) echo "unknown: $1" >&2; exit 1 ;;
  esac
done

export NEXUS_INSTALL_ROOT="${ROOT}"
export SG_ROOT="${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}"

log() { printf '[hostess7-github] %s\n' "$*"; }

RSYNC_EXCLUDES=(
  --exclude='.git'
  --exclude='.pages-hub-*'
  --exclude='.wiki-*-publish'
  --exclude='.profile-*-publish'
  --exclude='.pages-*-publish'
  --exclude='data/combinatronic-visuals'
  --exclude='data/combinatronic-visuals/**'
  --exclude='panel/profile-*'
  --exclude='Grok16/vendor'
  --exclude='Grok16/vendor/**'
  --exclude='_archive'
  --exclude='_archive/**'
  --exclude='.nexus-field-drive'
  --exclude='.nexus-field-drive/**'
  --exclude='KILROY/build'
  --exclude='KILROY/build/**'
  --exclude='.nexus-state'
  --exclude='.nexus-state-test'
  --exclude='.nexus-state-test-isolated'
  --exclude='dist'
  --exclude='cache'
  --exclude='state'
  --exclude='Hostess7/cache'
  --exclude='Hostess7/zac'
  --exclude='Queen/vendor'
  --exclude='Queen/cache'
  --exclude='Queen/build'
  --exclude='Queen/build-*'
  --exclude='Queen/field-gecko/profile'
  --exclude='Queen/.venv*'
  --exclude='__pycache__'
  --exclude='*.pyc'
  --exclude='*.log'
  --exclude='*.jsonl'
  --exclude='*.img'
  --exclude='linux-kernel'
  --exclude='linux-kernel/**'
  --exclude='GIMP-Field/tree/linux-kernel'
  --exclude='GIMP-Field/tree/linux-kernel/**'
)

STACK_SYMLINKS=(
  AMOURANTHRTX Grok16 GrokPy PythonG KILROY Final_Eye Final_Ear GrokLab
  ZNEWOCR ZOCR ZNetwork World_Redata World_Repack Field_Primer Spiderweb
  AmmoCode Field_Research Kill-Grok-Orphans
)

PRUNE_GLOBS=(
  '.pages-hub-*'
  '.wiki-*-publish'
  '.profile-*-publish'
  '.pages-*-publish'
  '.git'
  '.nexus-state'
  '.nexus-state-test'
  '.nexus-state-test-isolated'
  '.nexus-field-drive'
  '_archive'
  'dist'
  'cache'
  'state'
  'linux-kernel'
)

materialize_siblings() {
  local name link target copied
  for name in "${STACK_SYMLINKS[@]}"; do
    link="${STAGE}/${name}"
    [[ -L "$link" ]] || continue
    target="$(readlink -f "$link" 2>/dev/null || true)"
    [[ -n "$target" && -d "$target" ]] || continue
    log "materialize ${name} ← ${target}"
    rm -f "$link"
    mkdir -p "$link"
    copied=0
    if rsync -a \
      --exclude='.git' --exclude='build' --exclude='build-cmake' --exclude='cache'
      --exclude='vendor' --exclude='.venv*' --exclude='__pycache__' --exclude='*.pyc' \
      "${target}/" "${link}/" 2>/dev/null; then
      copied=1
    fi
    if [[ "$copied" -eq 0 ]]; then
      rsync -a --ignore-errors \
        --exclude='.git' --exclude='build' --exclude='vendor' --exclude='.venv*' \
        "${target}/" "${link}/" || true
    fi
  done
}

prune_not_in_set() {
  local g path
  log "prune paths not in release set"
  for g in "${PRUNE_GLOBS[@]}"; do
    for path in "${STAGE}"/${g}; do
      [[ -e "$path" ]] || continue
      log "  remove ${path#"${STAGE}/"}"
      rm -rf "$path"
    done
  done
  find "$STAGE" -type d -name '.git' -prune -exec rm -rf {} + 2>/dev/null || true
  find "$STAGE" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
  find "$STAGE" -type f -name '*.pyc' -delete 2>/dev/null || true
  log "prune files >95MB (GitHub limit)"
  while IFS= read -r -d '' blob; do
    log "  drop ${blob#"${STAGE}/"}"
    rm -f "$blob"
  done < <(find "$STAGE" -type f -size +95M -print0 2>/dev/null || true)
}

stage_tree() {
  log "stage NewLatest → ${STAGE}"
  rm -rf "$STAGE"
  mkdir -p "$STAGE"
  rsync -a "${RSYNC_EXCLUDES[@]}" "${ROOT}/" "${STAGE}/"
  materialize_siblings
  prune_not_in_set
  [[ -f "${ROOT}/README-HOSTESS7.md" ]] && cp "${ROOT}/README-HOSTESS7.md" "${STAGE}/README.md"
  [[ -f "${ROOT}/LICENSE-HOSTESS7" ]] && cp "${ROOT}/LICENSE-HOSTESS7" "${STAGE}/LICENSE"
  [[ -d "${ROOT}/wiki-hostess7" ]] && mkdir -p "${STAGE}/wiki" && rsync -a "${ROOT}/wiki-hostess7/" "${STAGE}/wiki/"
  log "stage size: $(du -sh "$STAGE" | awk '{print $1}')"
}

git_publish_stage() {
  if [[ "$DRY" -eq 1 ]]; then
    log "dry-run: would git push ${STAGE} → ${REMOTE}"
    return 0
  fi
  cd "$STAGE"
  rm -rf .git
  git init -b main
  git config user.email "${GIT_USER_EMAIL:-gzac5314@users.noreply.github.com}"
  git config user.name "${GIT_USER_NAME:-ZacharyGeurts}"
  git add -A
  git commit -m "Hostess7 ${HOSTESS7_VERSION} — full NewLatest field stack package" || true
  if ! gh repo view ZacharyGeurts/Hostess7 >/dev/null 2>&1; then
    gh repo create Hostess7 --public \
      --description "Hostess 7 beta — brain hub + full AmmoOS field stack" \
      --homepage "https://zacharygeurts.github.io/Hostess7/"
  fi
  git remote remove origin 2>/dev/null || true
  git remote add origin "$REMOTE"
  git config http.postBuffer 524288000
  git config http.lowSpeedLimit 0
  git config http.lowSpeedTime 999999
  log "git push origin main"
  git push -u origin main --force
  git tag -a "$TAG" -m "Hostess7 ${HOSTESS7_VERSION}" 2>/dev/null || git tag -f "$TAG" -m "Hostess7 ${HOSTESS7_VERSION}"
  git push origin "$TAG" --force 2>/dev/null || log "WARN tag push skipped"
}

log "Hostess7 GitHub publish — version ${HOSTESS7_VERSION}"
stage_tree

if [[ -f "${ROOT}/scripts/seal-built-executables.sh" ]]; then
  log "seal executables in stage"
  NEXUS_INSTALL_ROOT="$STAGE" NEXUS_STATE_DIR="${STAGE}/.nexus-state" \
    bash "${ROOT}/scripts/seal-built-executables.sh" 2>/dev/null || log "WARN seal partial"
  rm -rf "${STAGE}/.nexus-state" 2>/dev/null || true
fi

if [[ "$PUSH" -eq 0 ]]; then
  log "staged at ${STAGE} — pass --push to publish"
  exit 0
fi

git_publish_stage
log "published → https://github.com/ZacharyGeurts/Hostess7"