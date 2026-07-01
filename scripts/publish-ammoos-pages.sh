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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/publish-ammoos-pages.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Publish AmmoOS docs/ to GitHub Pages (gh-pages branch).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOCS_SRC="${ROOT}/docs"
PAGES_REPO="${PAGES_REPO:-${ROOT}/.pages-ammoos-publish}"
PAGES_REMOTE="${PAGES_REMOTE:-https://github.com/ZacharyGeurts/AmmoOS.git}"
PAGES_BRANCH="${PAGES_BRANCH:-gh-pages}"
VER="${AMMOOS_VERSION:-2.0.0-beta}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version) VER="$2"; shift 2 ;;
    --remote) PAGES_REMOTE="$2"; shift 2 ;;
    *) shift ;;
  esac
done

[[ -d "$DOCS_SRC" ]] || { echo "Missing docs/" >&2; exit 1; }

if [[ -f "${ROOT}/docs/build-ammoos-manual.py" ]]; then
  python3 "${ROOT}/docs/build-ammoos-manual.py"
fi

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
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='build-ammoos-manual.py' \
  --exclude='capture-*.py' \
  "${DOCS_SRC}/" "${PAGES_REPO}/"

cd "$PAGES_REPO"
git add -A
if git diff --cached --quiet; then
  if git rev-parse HEAD >/dev/null 2>&1; then
    echo "Pages up to date"
    exit 0
  fi
  git -c user.email="gzac5314@users.noreply.github.com" -c user.name="ZacharyGeurts" \
    commit --allow-empty -m "pages: init gh-pages v${VER}"
else
  git -c user.email="gzac5314@users.noreply.github.com" -c user.name="ZacharyGeurts" \
    commit -m "pages: AmmoOS manual v${VER}"
fi
git push origin "$PAGES_BRANCH" 2>/dev/null || git push -u origin "$PAGES_BRANCH"
echo "Pages: https://zacharygeurts.github.io/AmmoOS/"