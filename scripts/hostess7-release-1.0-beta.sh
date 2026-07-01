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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/hostess7-release-1.0-beta.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Hostess7 1.0.0-beta — complete stack release to github.com/ZacharyGeurts/Hostess7
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
[[ -f "${ROOT}/lib/nexus-common.sh" ]] && source "${ROOT}/lib/nexus-common.sh"
nexus_release_host_path 2>/dev/null || export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

HOSTESS7_VERSION="${HOSTESS7_VERSION:-1.0.0-beta}"
TAG="v${HOSTESS7_VERSION}"
PUSH=0
SKIP_PRE=0
SKIP_PACK=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --push) PUSH=1; shift ;;
    --skip-pre) SKIP_PRE=1; shift ;;
    --skip-pack) SKIP_PACK=1; shift ;;
    -v|--version) HOSTESS7_VERSION="$2"; TAG="v${HOSTESS7_VERSION}"; shift 2 ;;
    *) echo "unknown: $1" >&2; exit 1 ;;
  esac
done

export SG_ROOT="${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}"
export HOSTESS7_VERSION NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"

PROGRESS="${NEXUS_STATE_DIR}/hostess7-release-progress.json"
mkdir -p "$NEXUS_STATE_DIR"

progress_write() {
  local step="$1" status="$2" detail="${3:-}"
  python3 - <<PY
import json
from datetime import datetime, timezone
from pathlib import Path

path = Path("${PROGRESS}")
doc = {"product": "Hostess7", "version": "${HOSTESS7_VERSION}", "tag": "${TAG}", "steps": []}
if path.is_file():
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
doc["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
steps = doc.setdefault("steps", [])
found = False
for s in steps:
    if s.get("id") == "${step}":
        s["status"] = "${status}"
        s["detail"] = """${detail}"""
        s["at"] = doc["updated_at"]
        found = True
        break
if not found:
    steps.append({"id": "${step}", "status": "${status}", "detail": """${detail}""", "at": doc["updated_at"]})
path.write_text(json.dumps(doc, indent=2) + "\\n", encoding="utf-8")
PY
}

log() {
  printf '[%s] hostess7-release %s\n' "$(date +%H:%M:%S)" "$*"
}

step() {
  local id="$1" label="$2"
  shift 2
  log "START ${label}"
  progress_write "$id" "running" "$label"
  if "$@"; then
    log "DONE ${label}"
    progress_write "$id" "ok" "$label"
    return 0
  fi
  log "WARN ${label} — continuing"
  progress_write "$id" "warn" "$label"
  return 0
}

log "Hostess7 ${HOSTESS7_VERSION} release — AML boundary on, live progress"
progress_write "init" "running" "release started"

if [[ "$SKIP_PRE" -eq 0 ]]; then
  step "pre-update" "Hostess7 pre-update (AML)" bash "${ROOT}/lib/ammolang-run.sh" hostess7_pre_update
else
  log "SKIP pre-update"
  progress_write "pre-update" "skipped" "SKIP_PRE=1"
fi

step "h7b-pack" "H7B brain pack (curiosity)" bash -c "
  python3 '${ROOT}/lib/field-h7b-brain-storage.py' pack 2>/dev/null || true
"

DIST="${ROOT}/dist"
need_pack=1
min_src_bytes=$((200 * 1024 * 1024))
if [[ "$SKIP_PACK" -eq 1 ]]; then
  src_arc="${DIST}/hostess7-${HOSTESS7_VERSION}-source.h7e"
  inst_arc="${DIST}/hostess7-${HOSTESS7_VERSION}-installers.tar.gz"
  if [[ -f "$src_arc" && -f "$inst_arc" ]]; then
    sz=$(stat -c%s "$src_arc" 2>/dev/null || echo 0)
    if [[ "$sz" -ge "$min_src_bytes" ]]; then
      need_pack=0
      log "SKIP pack — dist artifacts present ($(du -h "$src_arc" | awk '{print $1}'))"
      progress_write "pack" "skipped" "existing archives"
    fi
  fi
fi
if [[ "$need_pack" -eq 1 ]]; then
  step "pack" "pack archives" bash "${ROOT}/scripts/pack-hostess7-release.sh" --version "$HOSTESS7_VERSION"
fi

EXPORT="${DIST}/hostess7-export-${HOSTESS7_VERSION}"
step "export-stage" "stage export tree" bash -c "
  rm -rf '${EXPORT}'
  mkdir -p '${EXPORT}'
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
    '${DIST}/hostess7-${HOSTESS7_VERSION}/' '${EXPORT}/'
  echo '=== prune export blobs >95MB ==='
  find '${EXPORT}' -type f -size +95M -delete 2>/dev/null || true
  cp -f '${ROOT}/README-HOSTESS7.md' '${EXPORT}/README.md'
  cp -f '${ROOT}/LICENSE-HOSTESS7' '${EXPORT}/LICENSE'
"

if [[ "$PUSH" -eq 0 ]]; then
  log "export ready at ${EXPORT} (pass --push to publish)"
  progress_write "publish" "ready" "export staged — pass --push"
  exit 0
fi

step "git-init" "git init + commit" bash -c "
  cd '${EXPORT}'
  if [[ ! -d .git ]]; then
    git init -b main
    git config user.email 'gzac5314@users.noreply.github.com'
    git config user.name 'ZacharyGeurts'
  fi
  git add -A
  git commit -m 'Hostess7 ${HOSTESS7_VERSION} beta — complete field stack (AmmoOS, Grok16, Queen)' || true
"

REMOTE="https://github.com/ZacharyGeurts/Hostess7.git"
step "repo-create" "GitHub repo Hostess7" bash -c "
  if ! gh repo view ZacharyGeurts/Hostess7 >/dev/null 2>&1; then
    gh repo create Hostess7 --public \
      --description 'Hostess 7 beta — brain hub + AmmoOS + Grok16 + Queen field stack' \
      --homepage 'https://zacharygeurts.github.io/Hostess7/'
  fi
"

step "git-push" "git push main" bash -c "
  cd '${EXPORT}'
  git remote remove origin 2>/dev/null || true
  git remote add origin '${REMOTE}'
  git config http.postBuffer 524288000
  git config http.lowSpeedLimit 0
  git config http.lowSpeedTime 999999
  git push -u origin main --force || echo 'WARN push partial'
  git tag -a '${TAG}' -m 'Hostess7 ${HOSTESS7_VERSION}' 2>/dev/null || git tag -f '${TAG}' -m 'Hostess7 ${HOSTESS7_VERSION}'
  git push origin '${TAG}' --force 2>/dev/null || echo 'WARN tag push skipped'
"

NOTES="${ROOT}/RELEASE-${HOSTESS7_VERSION}.md"
[[ -f "$NOTES" ]] || NOTES="${ROOT}/RELEASE-1.0.0-beta.md"

step "gh-release" "GitHub release ${TAG}" bash -c "
  assets=()
  max_asset_bytes=\$((2 * 1024 * 1024 * 1024))
  for a in \
    '${DIST}/hostess7-${HOSTESS7_VERSION}-source.h7e' \
    '${DIST}/hostess7-${HOSTESS7_VERSION}-installers.tar.gz' \
    '${DIST}/hostess7-${HOSTESS7_VERSION}-windows-x86_64.zip' \
    '${DIST}/hostess7-${HOSTESS7_VERSION}-platforms.json' \
    '${DIST}/hostess7-${HOSTESS7_VERSION}-PLATFORMS.md'; do
    [[ -f \"\$a\" ]] || continue
    sz=\$(stat -c%s \"\$a\" 2>/dev/null || echo 0)
    if [[ \"\$sz\" -gt \"\$max_asset_bytes\" ]]; then
      echo \"skip asset \$(basename \"\$a\") — over 2GiB\"
      continue
    fi
    assets+=(\"\$a\")
  done
  if gh release view '${TAG}' >/dev/null 2>&1; then
    gh release edit '${TAG}' --title 'Hostess7 ${HOSTESS7_VERSION}' --notes-file '${NOTES}'
    [[ \${#assets[@]} -gt 0 ]] && gh release upload '${TAG}' \"\${assets[@]}\" --clobber
  else
    gh release create '${TAG}' --title 'Hostess7 ${HOSTESS7_VERSION}' --notes-file '${NOTES}' \"\${assets[@]}\"
  fi
"

step "gh-pages" "GitHub Pages Talk & Draw" bash -c "
  HOSTESS7_VERSION='${HOSTESS7_VERSION}' bash '${ROOT}/scripts/publish-hostess7-pages.sh'
"

log "released ${TAG} → https://github.com/ZacharyGeurts/Hostess7/releases/tag/${TAG}"
progress_write "complete" "ok" "released ${TAG}"