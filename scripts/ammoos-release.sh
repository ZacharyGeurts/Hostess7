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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/ammoos-release.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# AmmoOS beta release — pipeline, pack, publish to github.com/ZacharyGeurts/AmmoOS
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
[[ -f "${ROOT}/lib/nexus-common.sh" ]] && source "${ROOT}/lib/nexus-common.sh"
nexus_release_host_path 2>/dev/null || export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
SG_ROOT="${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}"
AMMOOS_VERSION="${AMMOOS_VERSION:-2.0.0-beta5}"
TAG="v${AMMOOS_VERSION}"
PUSH=0

for arg in "$@"; do
  case "$arg" in
    --push) PUSH=1 ;;
    -v|--version) AMMOOS_VERSION="${2:-$AMMOOS_VERSION}"; TAG="v${AMMOOS_VERSION}" ;;
  esac
done

export SG_ROOT AMMOOS_VERSION NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"

log() { printf '[%s] ammoos-release %s\n' "$(date +%H:%M:%S)" "$*"; }

if [[ "${SKIP_BETA_PIPELINE:-0}" != "1" ]]; then
  log "beta pipeline (AmmoLang)"
  bash "${ROOT}/scripts/ammoos-beta-pipeline.sh" || {
    log "WARN beta pipeline partial — continuing pack (SKIP_BETA_PIPELINE=1 to skip)"
  }
else
  log "SKIP beta pipeline"
fi

log "build manual"
if [[ -f "${ROOT}/docs/build-ammoos-manual.py" ]]; then
  python3 "${ROOT}/docs/build-ammoos-manual.py"
fi

need_pack=1
min_src_bytes=$((500 * 1024 * 1024))
if [[ "${SKIP_PACK:-0}" == "1" ]]; then
  src_arc="${ROOT}/dist/ammoos-${AMMOOS_VERSION}-source.h7e"
  inst_arc="${ROOT}/dist/ammoos-${AMMOOS_VERSION}-installers.tar.gz"
  src_ok=0
  if [[ -f "$src_arc" ]]; then
    sz=$(stat -c%s "$src_arc" 2>/dev/null || echo 0)
    [[ "$sz" -ge "$min_src_bytes" ]] && src_ok=1
  fi
  if [[ "$src_ok" -eq 1 && -f "$inst_arc" ]]; then
    need_pack=0
    log "SKIP pack — dist artifacts present ($(du -h "$src_arc" | awk '{print $1}') source)"
  elif [[ -d "${ROOT}/dist/ammoos-${AMMOOS_VERSION}" ]]; then
    log "SKIP full pack — retar source from stage (corrupt or missing archive)"
    bash "${ROOT}/scripts/pack-ammoos-release.sh" --version "$AMMOOS_VERSION" --tar-only
    need_pack=0
  else
    log "SKIP_PACK set but archives missing — full pack"
  fi
fi
if [[ "$need_pack" -eq 1 ]]; then
  log "pack archives"
  bash "${ROOT}/scripts/pack-ammoos-release.sh" --version "$AMMOOS_VERSION"
fi

DIST="${ROOT}/dist"
EXPORT="${DIST}/ammoos-export-${AMMOOS_VERSION}"
rm -rf "$EXPORT"
mkdir -p "$EXPORT"

log "stage export tree for AmmoOS repo"
rsync -a --delete \
  --exclude='.git' \
  --exclude='dist' \
  --exclude='.nexus-state' \
  --exclude='cache' \
  --exclude='state' \
  --exclude='.github' \
  --exclude='linux-kernel' \
  --exclude='linux-kernel/**' \
  --exclude='_archive' \
  --exclude='_archive/**' \
  --exclude='.pages-hub-*' \
  --exclude='data/combinatronic-visuals' \
  --exclude='data/combinatronic-visuals/**' \
  --exclude='panel/profile-*' \
  --exclude='Grok16/vendor' \
  --exclude='Grok16/vendor/**' \
  --exclude='KILROY/build' \
  --exclude='KILROY/build/**' \
  --exclude='.venv*' \
  --exclude='**/.venv*' \
  "${DIST}/ammoos-${AMMOOS_VERSION}/" "$EXPORT/"

log "prune export blobs >95MB (GitHub limit)"
while IFS= read -r -d '' blob; do
  log "  drop ${blob#"$EXPORT"/}"
  rm -f "$blob"
done < <(find "$EXPORT" -type f -size +95M -print0 2>/dev/null || true)

if [[ "$PUSH" -eq 0 ]]; then
  log "export staged at ${EXPORT} (pass --push for git publish + gh release)"
  exit 0
fi

log "seal built executables"
bash "${ROOT}/scripts/seal-built-executables.sh" || log "WARN executable seal partial"

log "git publish — commit + push origin from ${ROOT}"
GIT_PUBLISH_MSG="AmmoOS ${AMMOOS_VERSION} beta — combinatronic field OS" \
  bash "${ROOT}/scripts/git-publish.sh" --siblings \
  || log "WARN git publish partial"

cd "$ROOT"
git tag -a "$TAG" -m "AmmoOS ${AMMOOS_VERSION}" 2>/dev/null || git tag -f "$TAG" -m "AmmoOS ${AMMOOS_VERSION}"
git push origin "$TAG" 2>/dev/null || log "WARN tag push skipped"

REMOTE="https://github.com/ZacharyGeurts/AmmoOS.git"

NOTES="${ROOT}/RELEASE-${AMMOOS_VERSION}.md"
assets=()
max_asset_bytes=$((2 * 1024 * 1024 * 1024))
for a in \
  "${DIST}/ammoos-${AMMOOS_VERSION}-source.h7e" \
  "${DIST}/ammoos-${AMMOOS_VERSION}-installers.tar.gz" \
  "${DIST}/ammoos-${AMMOOS_VERSION}-windows-x86_64.zip" \
  "${DIST}/ammoos-${AMMOOS_VERSION}-platforms.json" \
  "${DIST}/ammoos-${AMMOOS_VERSION}-PLATFORMS.md"; do
  [[ -f "$a" ]] || continue
  sz=$(stat -c%s "$a" 2>/dev/null || echo 0)
  if [[ "$sz" -gt "$max_asset_bytes" ]]; then
    log "skip release asset $(basename "$a") (${sz} bytes > 2GiB GitHub limit)"
    continue
  fi
  assets+=("$a")
done
VSYNC_VER="$(python3 -c "import json;from pathlib import Path;p=Path('${ROOT}/data/field-vsync-locker-version.json');print(json.loads(p.read_text()).get('version',''))" 2>/dev/null || true)"
if [[ -n "$VSYNC_VER" ]]; then
  for a in "${DIST}/vsync-locker-${VSYNC_VER}"-*.{tar.gz,zip,json}; do
    [[ -f "$a" ]] || continue
    sz=$(stat -c%s "$a" 2>/dev/null || echo 0)
    if [[ "$sz" -gt "$max_asset_bytes" ]]; then
      log "skip release asset $(basename "$a") (${sz} bytes > 2GiB GitHub limit)"
      continue
    fi
    assets+=("$a")
  done
fi

if gh release view "$TAG" >/dev/null 2>&1; then
  gh release edit "$TAG" --title "AmmoOS ${AMMOOS_VERSION}" --notes-file "$NOTES"
  [[ ${#assets[@]} -gt 0 ]] && gh release upload "$TAG" "${assets[@]}" --clobber
else
  gh release create "$TAG" --title "AmmoOS ${AMMOOS_VERSION}" --notes-file "$NOTES" "${assets[@]}"
fi

log "publish GitHub Pages"
bash "${ROOT}/scripts/publish-ammoos-pages.sh" --version "$AMMOOS_VERSION" --remote "$REMOTE"

log "publish AmmoOS wiki"
AMMOOS_VERSION="$AMMOOS_VERSION" bash "${ROOT}/scripts/publish-ammoos-wiki.sh" || log "WARN wiki publish partial"

log "publish stack hub + component Pages"
STACK_VERSION="$AMMOOS_VERSION" bash "${ROOT}/scripts/publish-stack-pages.sh" || log "WARN stack pages partial"

if [[ -f "${ROOT}/lib/github-profile-sync.py" ]]; then
  log "sync GitHub profile + favorites manifest"
  python3 "${ROOT}/lib/github-profile-sync.py" sync || log "WARN profile sync partial"
fi

log "released ${TAG} → https://github.com/ZacharyGeurts/AmmoOS/releases/tag/${TAG}"
log "manual → https://zacharygeurts.github.io/AmmoOS/"
log "wiki → https://github.com/ZacharyGeurts/AmmoOS/wiki"
log "stack → https://zacharygeurts.github.io/ZacharyGeurts/stack.html"