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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/publish-pages.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Publish docs/ to GitHub Pages (gh-pages branch).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOCS_SRC="${ROOT}/docs"
PAGES_REPO="${PAGES_REPO:-${ROOT}/.pages-publish}"
PAGES_REMOTE="${PAGES_REMOTE:-https://github.com/ZacharyGeurts/NEXUS-Shield.git}"
PAGES_BRANCH="${PAGES_BRANCH:-gh-pages}"

# shellcheck source=/dev/null
source "${ROOT}/lib/nexus-common.sh"
VER="${NEXUS_VERSION}"

if [[ ! -d "$DOCS_SRC" ]]; then
  echo "Missing ${DOCS_SRC}" >&2
  exit 1
fi

if [[ -x "${ROOT}/docs/gen-manual-images.py" ]] || [[ -f "${ROOT}/docs/gen-manual-images.py" ]]; then
  echo "=== regenerate manual SVGs ==="
  python3 "${ROOT}/docs/gen-manual-images.py" 2>/dev/null \
    || pythong "${ROOT}/docs/gen-manual-images.py" 2>/dev/null \
    || true
fi

if [[ ! -d "${PAGES_REPO}/.git" ]]; then
  rm -rf "$PAGES_REPO"
  if git ls-remote --heads "$PAGES_REMOTE" "$PAGES_BRANCH" | grep -q "$PAGES_BRANCH"; then
    git clone --branch "$PAGES_BRANCH" --single-branch "$PAGES_REMOTE" "$PAGES_REPO"
  else
    mkdir -p "$PAGES_REPO"
    git -C "$PAGES_REPO" init
    git -C "$PAGES_REPO" remote add origin "$PAGES_REMOTE"
    git -C "$PAGES_REPO" checkout -b "$PAGES_BRANCH" 2>/dev/null || git -C "$PAGES_REPO" branch -M "$PAGES_BRANCH"
  fi
fi

echo "=== rsync docs → gh-pages ==="
rsync -a --delete \
  --exclude='.git' \
  --exclude='capture-*.py' \
  --exclude='screenshots/*.png' \
  "${DOCS_SRC}/" "${PAGES_REPO}/"

cd "$PAGES_REPO"
git add -A
if git diff --cached --quiet; then
  echo "GitHub Pages already up to date."
  exit 0
fi
git commit -m "pages: NEXUS-Shield manual v${VER}"
git push origin "$PAGES_BRANCH" 2>/dev/null || git push -u origin "$PAGES_BRANCH"
echo "Pages published: https://zacharygeurts.github.io/NEXUS-Shield/"