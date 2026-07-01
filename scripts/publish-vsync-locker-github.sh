#!/usr/bin/env bash
# Stage VSYNC-Locker-only tree → dist/vsync-locker-github-publish, push ZacharyGeurts/VSYNC-Locker.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VER="$(python3 -c "import json;from pathlib import Path;d=json.loads(Path('${ROOT}/data/field-vsync-locker-version.json').read_text());print(d['version'])")"
TAG="v${VER}"
DIST="${ROOT}/dist"
STAGE="${DIST}/vsync-locker-github-publish"
REMOTE="${VSYNC_LOCKER_GITHUB_REMOTE:-git@github.com:ZacharyGeurts/VSYNC-Locker.git}"
REPO_SLUG="ZacharyGeurts/VSYNC-Locker"
PUSH=0
DRY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --push) PUSH=1; shift ;;
    --dry) DRY=1; shift ;;
    -v|--version) VER="$2"; TAG="v${VER}"; shift 2 ;;
    -h|--help)
      echo "Usage: publish-vsync-locker-github.sh [--push] [--dry] [-v VERSION]"
      exit 0
      ;;
    *) echo "unknown: $1" >&2; exit 1 ;;
  esac
done

log() { printf '[vsync-github] %s\n' "$*"; }

stage_tree() {
  log "stage locker-only → ${STAGE}"
  rm -rf "$STAGE"
  mkdir -p "${STAGE}/lib" "${STAGE}/data" "${STAGE}/panel" "${STAGE}/scripts" "${STAGE}/packaging"

  install -m 644 "${ROOT}/lib/field-vsync-locker.py" "${STAGE}/lib/"
  install -m 755 "${ROOT}/lib/field-vsync-locker-launch.sh" "${STAGE}/lib/"
  install -m 755 "${ROOT}/lib/field-vsync-locker-guard.sh" "${STAGE}/lib/"
  [[ -f "${ROOT}/lib/hardware_wire_registry.py" ]] && \
    install -m 644 "${ROOT}/lib/hardware_wire_registry.py" "${STAGE}/lib/"

  install -m 644 "${ROOT}/data/field-vsync-locker-doctrine.json" "${STAGE}/data/"
  install -m 644 "${ROOT}/data/field-vsync-locker-version.json" "${STAGE}/data/"
  install -m 644 "${ROOT}/data/field-vsync-locker-platform-release.json" "${STAGE}/data/"
  install -m 644 "${ROOT}/panel/field-vsync-locker.desktop" "${STAGE}/panel/"
  cp -a "${ROOT}/packaging/vsync-locker" "${STAGE}/packaging/"

  install -m 755 "${ROOT}/scripts/pack-vsync-locker.sh" "${STAGE}/scripts/"
  install -m 755 "${ROOT}/scripts/vsync-locker-release.sh" "${STAGE}/scripts/"
  install -m 755 "${ROOT}/scripts/publish-vsync-locker-github.sh" "${STAGE}/scripts/"

  [[ -f "${ROOT}/library/dewey/000-computer-science/ammolang/vsync_locker.aml" ]] && \
    install -m 644 "${ROOT}/library/dewey/000-computer-science/ammolang/vsync_locker.aml" "${STAGE}/vsync_locker.aml"

  [[ -f "${ROOT}/RELEASE-vsync-locker-${VER}.md" ]] && \
    cp "${ROOT}/RELEASE-vsync-locker-${VER}.md" "${STAGE}/RELEASE.md"
  [[ -f "${ROOT}/LICENSE" ]] && cp "${ROOT}/LICENSE" "${STAGE}/LICENSE"

  cat > "${STAGE}/README.md" <<EOF
# VSYNC-Locker ${VER}

Sovereign display timing protector — lock VSYNC cadence, baseline input surfaces, detect rogue overlays, and KILL trespassers.

Open-source hardened: security from host-bound secrets and integrity seals, not obscurity.

## Features

- Lock sovereign display timing (VSYNC / vblank)
- Baseline pointers, keyboards, and game controllers
- Anti-perfect-sync drift — unpredictable jitter exposes rogue overlays
- Background guard — double-click once, stays on patrol
- Foreign input detection (keyboard, control, pointer middlemen)

## Quick start (Linux)

\`\`\`bash
git clone https://github.com/ZacharyGeurts/VSYNC-Locker.git
cd VSYNC-Locker
python3 lib/field-vsync-locker.py harden
python3 lib/field-vsync-locker.py install-desktop
python3 lib/field-vsync-locker.py launch
python3 lib/field-vsync-locker.py guard --status
\`\`\`

Or install from a release tarball:

\`\`\`bash
tar -xzf vsync-locker-${VER}-linux-gnu-x86_64.tar.gz -C /opt/vsync-locker --strip-components=1
sudo packaging/vsync-locker/linux/install.sh
\`\`\`

## Platforms

See [Releases](https://github.com/ZacharyGeurts/VSYNC-Locker/releases) for Linux, macOS, Windows, FreeBSD, and Android (Termux) packages.

## Build packages locally

\`\`\`bash
bash scripts/pack-vsync-locker.sh
\`\`\`

## License

See LICENSE in this repository.
EOF

  cat > "${STAGE}/.gitignore" <<'EOF'
.nexus-state/
dist/
__pycache__/
*.pyc
*.log
*.jsonl
packaging/vsync-locker/native/bin/
packaging/vsync-locker/native/dist-bin/
EOF

  printf '%s\n' "$VER" > "${STAGE}/VERSION"
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
  git commit -m "VSYNC-Locker ${VER} — sovereign display timing guard" || true

  if ! gh repo view "$REPO_SLUG" >/dev/null 2>&1; then
    log "create ${REPO_SLUG}"
    gh repo create VSYNC-Locker --public \
      --description "VSYNC-Locker — sovereign display timing, input guard, anti-perfect-sync drift" \
      --homepage "https://github.com/ZacharyGeurts/VSYNC-Locker"
  fi

  git remote remove origin 2>/dev/null || true
  git remote add origin "$REMOTE"
  git config http.postBuffer 524288000
  git config http.lowSpeedLimit 0
  git config http.lowSpeedTime 999999
  log "git push origin main"
  git push -u origin main --force
  git tag -a "$TAG" -m "VSYNC-Locker ${VER}" 2>/dev/null || git tag -f "$TAG" -m "VSYNC-Locker ${VER}"
  git push origin "$TAG" --force 2>/dev/null || log "WARN tag push skipped — gh release uses --target main"
}

publish_release() {
  local notes="${ROOT}/RELEASE-vsync-locker-${VER}.md"
  [[ -f "$notes" ]] || notes="${ROOT}/data/field-vsync-locker-doctrine.json"
  local assets=()
  for a in "${ROOT}/dist/vsync-locker-${VER}"-*.{tar.gz,zip,json}; do
    [[ -f "$a" ]] && assets+=("$a")
  done
  [[ -f "${ROOT}/dist/vsync-locker-${VER}-MANIFEST.txt" ]] && \
    assets+=("${ROOT}/dist/vsync-locker-${VER}-MANIFEST.txt")

  if [[ "$DRY" -eq 1 ]]; then
    log "dry-run: would gh release ${TAG} on ${REPO_SLUG} (${#assets[@]} assets)"
    return 0
  fi

  if gh release view "$TAG" --repo "$REPO_SLUG" >/dev/null 2>&1; then
    gh release edit "$TAG" --repo "$REPO_SLUG" --title "VSYNC-Locker ${VER}" --notes-file "$notes"
    [[ ${#assets[@]} -gt 0 ]] && gh release upload "$TAG" --repo "$REPO_SLUG" --clobber "${assets[@]}"
  else
    gh release create "$TAG" \
      --repo "$REPO_SLUG" \
      --target main \
      --title "VSYNC-Locker ${VER}" \
      --notes-file "$notes" \
      "${assets[@]}"
  fi
  log "release → https://github.com/${REPO_SLUG}/releases/tag/${TAG}"
}

log "VSYNC-Locker GitHub publish — version ${VER}"
stage_tree

if [[ "$PUSH" -eq 0 ]]; then
  log "staged at ${STAGE} — pass --push to publish"
  exit 0
fi

git_publish_stage
publish_release
log "published → https://github.com/${REPO_SLUG}"