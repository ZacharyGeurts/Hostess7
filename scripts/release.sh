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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/release.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS-Shield release — tag and publish GitHub release.
# Policy: every update is a full minor version (X.Y.0). Run bump-version.sh first.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
source "${ROOT}/lib/nexus-common.sh"

usage() {
  cat <<'EOF'
Usage: release.sh [--version VER] [--dry-run] [--help]

  --version VER   Override NEXUS_VERSION for this release
  --dry-run       Show planned tag/pack steps without git push or gh publish
  --help          Show this help
EOF
}

DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    -n|--dry-run) DRY_RUN=1; shift ;;
    -v|--version)
      [[ $# -ge 2 ]] || { echo "--version requires a value" >&2; exit 1; }
      NEXUS_VERSION="$2"
      shift 2
      ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ ! "${NEXUS_VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "Release requires NEXUS_VERSION=X.Y.Z (got ${NEXUS_VERSION}). Use scripts/bump-version.sh" >&2
  exit 1
fi

TAG="v${NEXUS_VERSION}"
NOTES="${ROOT}/RELEASE-${NEXUS_VERSION}.md"

if [[ ! -f "$NOTES" ]]; then
  cat >"$NOTES" <<EOF
# NEXUS-Shield ${NEXUS_VERSION}

- Hostess7 unified operator — autonomous field sync and GitHub update planning
- Panel: live fetch only — no client cache or field-snapshot stubs
- Hell Kit: sever wire, regional disable, human threat sweep
- Precision map & spiderweb with sub-micron GPS placement
- Dark dropdown styling across panel selects

Install: \`sudo ./stealth_install.sh\` from source tree.
Panel: https://127.0.0.1:9477/field
EOF
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "dry-run: would tag ${TAG}, commit, push, pack, publish via gh"
  echo "notes: ${NOTES}"
  exit 0
fi

cd "$ROOT"
# Stage only versioned source — never runtime logs/state (amouranth_engine.log exceeds GitHub limits).
git add -u
git add RELEASE-*.md README.md INSTALL-README.md SECURITY.md lib/nexus-common.sh scripts/ 2>/dev/null || true
if ! git diff --cached --quiet; then
  git commit -m "release: NEXUS-Shield ${NEXUS_VERSION}" || true
fi

git tag -a "$TAG" -m "NEXUS-Shield ${NEXUS_VERSION}" 2>/dev/null || git tag -f "$TAG" -m "NEXUS-Shield ${NEXUS_VERSION}"
git push origin main
git push origin "$TAG" --force

if [[ -x "${ROOT}/scripts/pack-release.sh" ]]; then
  bash "${ROOT}/scripts/pack-release.sh"
fi

if [[ -x "${ROOT}/scripts/nexus-release-finalize.sh" ]]; then
  bash "${ROOT}/scripts/nexus-release-finalize.sh" --skip-pack
fi

if command -v gh >/dev/null 2>&1; then
  assets=()
  for asset in "${ROOT}/dist/nexus-shield-${NEXUS_VERSION}-source.tar.gz" \
    "${ROOT}/dist/nexus-shield-${NEXUS_VERSION}-installers.tar.gz"; do
    [[ -f "$asset" ]] && assets+=("$asset")
  done
  if gh release view "$TAG" >/dev/null 2>&1; then
    gh release edit "$TAG" --title "NEXUS-Shield ${NEXUS_VERSION}" --notes-file "$NOTES" 2>/dev/null || true
    [[ ${#assets[@]} -gt 0 ]] && gh release upload "$TAG" "${assets[@]}" --clobber 2>/dev/null || true
  else
    if [[ ${#assets[@]} -gt 0 ]]; then
      gh release create "$TAG" --title "NEXUS-Shield ${NEXUS_VERSION}" --notes-file "$NOTES" "${assets[@]}"
    else
      gh release create "$TAG" --title "NEXUS-Shield ${NEXUS_VERSION}" --notes-file "$NOTES" 2>/dev/null \
        || gh release edit "$TAG" --notes-file "$NOTES" 2>/dev/null || true
    fi
  fi
  echo "Release ${TAG} published via gh"
else
  echo "Tagged ${TAG}. Install gh CLI to auto-publish release notes."
fi