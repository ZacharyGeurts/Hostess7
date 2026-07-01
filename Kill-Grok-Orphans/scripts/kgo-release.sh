#!/usr/bin/env bash
# Kill Grok Orphans release — build all platforms, tag, push via gh (MCP layer companion)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(tr -d '\n' < "${ROOT}/VERSION")"
TAG="v${VERSION}"
PUSH=0

for arg in "$@"; do
  case "$arg" in
    --push) PUSH=1 ;;
  esac
done

log() { printf '[%s] kgo-release %s\n' "$(date +%H:%M:%S)" "$*"; }

log "build all platforms"
bash "${ROOT}/scripts/build-all-platforms.sh"

cd "${ROOT}"
if [[ -d .git ]]; then
  git add -A
  if git diff --cached --quiet; then
    log "no git changes"
  else
    git commit -m "Kill Grok Orphans ${VERSION} — fast scan, all Grok16 platforms"
  fi
fi

if [[ "$PUSH" -eq 0 ]]; then
  log "built at ${ROOT}/dist (pass --push to publish)"
  exit 0
fi

REMOTE="https://github.com/ZacharyGeurts/Kill-Grok-Orphans.git"
if [[ -d .git ]]; then
  git push origin main
  git tag -a "$TAG" -m "Kill Grok Orphans ${VERSION} — fast multi-platform watchdog" 2>/dev/null \
    || git tag -f "$TAG" -m "Kill Grok Orphans ${VERSION}"
  git push origin "$TAG" --force
fi

NOTES="${ROOT}/RELEASE-${VERSION}.md"
[[ -f "$NOTES" ]] || NOTES="${ROOT}/README.md"

assets=()
for a in "${ROOT}/dist/kgo-${VERSION}"-*.{tar.gz,zip}; do
  [[ -f "$a" ]] && assets+=("$a")
done

gh release view "$TAG" --repo ZacharyGeurts/Kill-Grok-Orphans >/dev/null 2>&1 \
  && gh release upload "$TAG" --repo ZacharyGeurts/Kill-Grok-Orphans --clobber "${assets[@]}" \
  || gh release create "$TAG" \
       --repo ZacharyGeurts/Kill-Grok-Orphans \
       --title "Kill Grok Orphans ${VERSION}" \
       --notes-file "$NOTES" \
       "${assets[@]}"

log "published https://github.com/ZacharyGeurts/Kill-Grok-Orphans/releases/tag/${TAG}"