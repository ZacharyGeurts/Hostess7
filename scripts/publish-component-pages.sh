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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/publish-component-pages.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Publish a component docs/ tree to GitHub Pages (gh-pages branch).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOCS_SRC=""
PAGES_REPO=""
PAGES_REMOTE=""
PAGES_BRANCH="${PAGES_BRANCH:-gh-pages}"
VER="${COMPONENT_VERSION:-stack}"
NAME="component"

usage() {
  echo "Usage: $0 --name Queen --docs profile/queen-publish/docs --remote https://github.com/ZacharyGeurts/Queen.git [--version 1.0]" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) NAME="$2"; shift 2 ;;
    --docs) DOCS_SRC="$2"; shift 2 ;;
    --repo) PAGES_REPO="$2"; shift 2 ;;
    --remote) PAGES_REMOTE="$2"; shift 2 ;;
    --version) VER="$2"; shift 2 ;;
    *) shift ;;
  esac
done

[[ -n "$DOCS_SRC" ]] || usage
[[ "$DOCS_SRC" != /* ]] && DOCS_SRC="${ROOT}/${DOCS_SRC}"
[[ -d "$DOCS_SRC" ]] || { echo "Missing docs: ${DOCS_SRC}" >&2; exit 1; }
[[ -n "$PAGES_REMOTE" ]] || { echo "Missing --remote" >&2; exit 1; }
PAGES_REPO="${PAGES_REPO:-${ROOT}/.pages-${NAME}-publish}"

if [[ ! -d "${PAGES_REPO}/.git" ]]; then
  rm -rf "$PAGES_REPO"
  if git ls-remote --heads "$PAGES_REMOTE" "$PAGES_BRANCH" 2>/dev/null | grep -q "$PAGES_BRANCH"; then
    git clone --branch "$PAGES_BRANCH" --single-branch "$PAGES_REMOTE" "$PAGES_REPO"
  else
    mkdir -p "$PAGES_REPO"
    git -C "$PAGES_REPO" init -b "$PAGES_BRANCH"
    git -C "$PAGES_REPO" remote add origin "$PAGES_REMOTE"
  fi
fi

rsync -a --delete \
  --exclude='.git' \
  --exclude='README.md' \
  "${DOCS_SRC}/" "${PAGES_REPO}/"

# Copy sibling assets when publish tree uses ../assets (Queen hub pattern).
PARENT="$(dirname "$DOCS_SRC")"
if [[ -d "${PARENT}/assets" ]]; then
  rsync -a "${PARENT}/assets/" "${PAGES_REPO}/assets/"
fi

cd "$PAGES_REPO"
git add -A
git diff --cached --quiet && { echo "${NAME} pages up to date"; exit 0; }
git -c user.email="gzac5314@users.noreply.github.com" -c user.name="ZacharyGeurts" \
  commit -m "pages: ${NAME} v${VER}"
git push origin "$PAGES_BRANCH" 2>/dev/null || git push -u origin "$PAGES_BRANCH"
echo "Pages: https://zacharygeurts.github.io/${NAME}/"