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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/publish-ammoos-wiki.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Publish AmmoOS wiki/*.md → github.com/ZacharyGeurts/AmmoOS.wiki
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WIKI_SRC="${ROOT}/wiki"
WIKI_REPO="${WIKI_REPO:-${ROOT}/.wiki-ammoos-publish}"
WIKI_REMOTE="${WIKI_REMOTE:-https://github.com/ZacharyGeurts/AmmoOS.wiki.git}"
VER="${AMMOOS_VERSION:-2.0.0-beta5}"
REPO="${AMMOOS_GITHUB_REPO:-ZacharyGeurts/AmmoOS}"

[[ -d "$WIKI_SRC" ]] || { echo "Missing ${WIKI_SRC}" >&2; exit 1; }

gh repo edit "$REPO" --enable-wiki 2>/dev/null || true

# Bootstrap wiki git repo on GitHub when .wiki clone is not yet provisioned.
if ! git ls-remote "$WIKI_REMOTE" HEAD 2>/dev/null | grep -q .; then
  home_md="${WIKI_SRC}/Home.md"
  if [[ -f "$home_md" ]]; then
    gh api "repos/${REPO}/wiki/pages" \
      -f title=Home \
      -f body="$(cat "$home_md")" 2>/dev/null || true
  fi
fi

if [[ ! -d "${WIKI_REPO}/.git" ]]; then
  rm -rf "$WIKI_REPO"
  if git ls-remote --heads "$WIKI_REMOTE" master 2>/dev/null | grep -q master; then
    git clone "$WIKI_REMOTE" "$WIKI_REPO"
  elif git ls-remote --heads "$WIKI_REMOTE" main 2>/dev/null | grep -q main; then
    git clone -b main "$WIKI_REMOTE" "$WIKI_REPO"
  else
    mkdir -p "$WIKI_REPO"
    git -C "$WIKI_REPO" init -b master
    git -C "$WIKI_REPO" remote add origin "$WIKI_REMOTE"
  fi
fi

rsync -a --delete --exclude='.git' "${WIKI_SRC}/" "${WIKI_REPO}/"

git -C "$WIKI_REPO" add -A
if git -C "$WIKI_REPO" diff --cached --quiet; then
  echo "AmmoOS wiki up to date"
  exit 0
fi
git -C "$WIKI_REPO" -c user.email="gzac5314@users.noreply.github.com" -c user.name="ZacharyGeurts" \
  commit -m "wiki: AmmoOS ${VER} — stack tie-in"
git -C "$WIKI_REPO" push origin master 2>/dev/null \
  || git -C "$WIKI_REPO" push origin main 2>/dev/null \
  || git -C "$WIKI_REPO" push -u origin HEAD
echo "Wiki: https://github.com/${REPO}/wiki"