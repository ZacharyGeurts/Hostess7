#!/usr/bin/env bash
# Stage GNUEOLTerminal book + terminal slice → dist/gnueol-terminal-github-publish, push ZacharyGeurts/GNUEOLTerminal.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VER="${GNUEOL_TERMINAL_VERSION:-3.0.7-beta5}"
DIST="${ROOT}/dist"
STAGE="${DIST}/gnueol-terminal-github-publish"
SRC="${ROOT}/GNUEOLTerminal"
REMOTE="${GNUEOL_TERMINAL_GITHUB_REMOTE:-git@github.com:ZacharyGeurts/GNUEOLTerminal.git}"
REPO_SLUG="ZacharyGeurts/GNUEOLTerminal"
PUSH=0
DRY=0
INVITE_RMS=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --push) PUSH=1; shift ;;
    --dry) DRY=1; shift ;;
    --invite-rms) INVITE_RMS=1; shift ;;
    -h|--help)
      echo "Usage: publish-gnueol-terminal-github.sh [--push] [--dry] [--invite-rms]"
      exit 0
      ;;
    *) echo "unknown: $1" >&2; exit 1 ;;
  esac
done

log() { printf '[gnueol-github] %s\n' "$*"; }

stage_tree() {
  log "stage GNUEOLTerminal → ${STAGE}"
  rm -rf "$STAGE"
  mkdir -p "$STAGE"

  rsync -a --delete \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    "${SRC}/" "${STAGE}/"

  mkdir -p "${STAGE}/lib" "${STAGE}/Queen/lib" "${STAGE}/Queen/world" "${STAGE}/data" "${STAGE}/docs/terminal"
  install -m 644 "${ROOT}/lib/field-gnu-terminal-iron-plate.py" "${STAGE}/lib/"
  install -m 644 "${ROOT}/lib/field-gnu-identity-verify.py" "${STAGE}/lib/"
  install -m 644 "${ROOT}/data/field-gnu-terminal-iron-plate-doctrine.json" "${STAGE}/data/"
  install -m 644 "${ROOT}/data/field-gnu-identity-doctrine.json" "${STAGE}/data/"
  install -m 644 "${ROOT}/Queen/lib/queen-terminal.py" "${STAGE}/Queen/lib/"
  install -m 644 "${ROOT}/panel/assets/field-gnu-terminal.js" "${STAGE}/docs/terminal/field-gnu-terminal.js" 2>/dev/null || true
  install -m 644 "${ROOT}/Queen/world/queen-gnu-terminal.js" "${STAGE}/Queen/world/"
  install -m 644 "${ROOT}/Queen/world/queen-gnu-terminal.css" "${STAGE}/Queen/world/"
  install -m 644 "${ROOT}/Queen/world/queen-gnu-terminal-embed.html" "${STAGE}/Queen/world/"
  for f in field-gnu-terminal.js field-gnu-terminal.css field-sovereign-bus.js; do
    [[ -f "${ROOT}/panel/assets/${f}" ]] && install -m 644 "${ROOT}/panel/assets/${f}" "${STAGE}/docs/terminal/${f}"
  done
  cp -a "${ROOT}/Queen/world/queen-gnu-terminal."* "${STAGE}/docs/terminal/" 2>/dev/null || true
  if [[ -f "${ROOT}/panel/field-gnu-terminal-embed.html" ]]; then
    cp "${ROOT}/panel/field-gnu-terminal-embed.html" "${STAGE}/docs/terminal/index.html"
  else
    cp "${ROOT}/Queen/world/queen-gnu-terminal-embed.html" "${STAGE}/docs/terminal/index.html"
  fi

  install -m 755 "${ROOT}/scripts/publish-gnueol-terminal-github.sh" "${STAGE}/scripts/" 2>/dev/null || \
    mkdir -p "${STAGE}/scripts" && install -m 755 "${ROOT}/scripts/publish-gnueol-terminal-github.sh" "${STAGE}/scripts/"

  [[ -f "${ROOT}/LICENSE" ]] && cp "${ROOT}/LICENSE" "${STAGE}/LICENSE"

  python3 "${STAGE}/scripts/forge-gnu-wiki-manual.py" 2>/dev/null || python3 "${ROOT}/GNUEOLTerminal/scripts/forge-gnu-wiki-manual.py"
  python3 "${STAGE}/scripts/forge-book.py" 2>/dev/null || python3 "${ROOT}/GNUEOLTerminal/scripts/forge-book.py"
  python3 "${STAGE}/scripts/build-site.py"
  touch "${STAGE}/docs/.nojekyll"
  [[ -d "${ROOT}/GNUEOLTerminal/assets/images" ]] && mkdir -p "${STAGE}/assets/images" && cp -a "${ROOT}/GNUEOLTerminal/assets/images/." "${STAGE}/assets/images/"

  printf '%s\n' "$VER" > "${STAGE}/VERSION"
  log "stage size: $(du -sh "$STAGE" | awk '{print $1}')"
}

git_publish_stage() {
  if [[ "$DRY" -eq 1 ]]; then
    log "dry-run: would git push ${STAGE} → ${REMOTE}"
    return 0
  fi
  H7_SECURE="${ROOT}/Hostess7/scripts/hostess7_secure_git.py"
  CLONE="${ROOT}/.gnueol-terminal-github-clone"
  PUBLISH_DIR="$CLONE"
  TAG="v${VER}"
  if [[ -f "$H7_SECURE" ]] && python3 "$H7_SECURE" verify >/dev/null 2>&1; then
    if [[ ! -d "${CLONE}/.git" ]]; then
      log "clone GNUEOLTerminal — preserve commit history"
      rm -rf "$CLONE"
      if ! python3 "$H7_SECURE" clone "$CLONE" --remote "$REMOTE" --branch main; then
        mkdir -p "$CLONE"
        cd "$CLONE" && git init -b main && cd "$ROOT"
      fi
    fi
    log "merge stage → clone (history preserved)"
    rsync -a --delete --exclude='.git' "${STAGE}/" "${CLONE}/"
    PUBLISH_DIR="$CLONE"
  else
    cd "$STAGE"
    rm -rf .git
    git init -b main
    PUBLISH_DIR="$STAGE"
  fi
  cd "$PUBLISH_DIR"
  git config user.email "${GIT_USER_EMAIL:-gzac5314@users.noreply.github.com}"
  git config user.name "${GIT_USER_NAME:-ZacharyGeurts}"
  git add -A
  git commit -m "GNUEOLTerminal ${VER} — Field Tech textbook · GNU wiki · iron plate" || true

  if ! gh repo view "$REPO_SLUG" >/dev/null 2>&1; then
    log "create ${REPO_SLUG}"
    gh repo create GNUEOLTerminal --public \
      --description "GNU EOL Terminal — book for Richard Stallman · shell ≡ terminal · iron plate" \
      --homepage "https://zacharygeurts.github.io/GNUEOLTerminal/"
    gh api "repos/${REPO_SLUG}/pages" -X POST -f build_type=workflow -f source[branch]=main -f source[path]=/ 2>/dev/null || true
  fi

  git remote remove origin 2>/dev/null || true
  git remote add origin "$REMOTE"
  git config http.postBuffer 524288000
  log "git push origin main (history preserved)"
  if [[ -f "$H7_SECURE" ]] && python3 "$H7_SECURE" verify >/dev/null 2>&1; then
    python3 "$H7_SECURE" push "$PUBLISH_DIR" --branch main \
      --remote "$REMOTE" --tag "$TAG" --force
  else
    git push -u origin main --force
    git tag -a "$TAG" -m "GNUEOLTerminal ${VER}" 2>/dev/null || git tag -f "$TAG" -m "GNUEOLTerminal ${VER}"
    git push origin "$TAG" --force 2>/dev/null || true
  fi
}

invite_rms() {
  if [[ "$DRY" -eq 1 ]]; then
    log "dry-run: would verify RMS and send collaborator invite"
    return 0
  fi
  PY="${PYTHON:-pythong}"
  if ! command -v "$PY" >/dev/null 2>&1; then PY=python3; fi
  log "verify RMS identity"
  "$PY" "${ROOT}/lib/field-gnu-identity-verify.py" json
  log "invite rms as read collaborator"
  "$PY" "${ROOT}/lib/field-gnu-identity-verify.py" invite || log "WARN invite skipped — verify failed or gh auth"
}

log "GNUEOLTerminal GitHub publish — version ${VER}"
stage_tree

if [[ "$PUSH" -eq 0 ]]; then
  log "staged at ${STAGE} — pass --push to publish"
  exit 0
fi

git_publish_stage
[[ "$INVITE_RMS" -eq 1 ]] && invite_rms
if command -v python3 >/dev/null 2>&1; then
  python3 "${ROOT}/lib/field-endpoint-registry.py" record pages publish_witness \
    "ZacharyGeurts/GNUEOLTerminal" "https://zacharygeurts.github.io/GNUEOLTerminal/" \
    publish-gnueol-terminal-github.sh "GNUEOLTerminal ${VER} pushed" 2>/dev/null || true
fi
log "published → https://zacharygeurts.github.io/GNUEOLTerminal/"