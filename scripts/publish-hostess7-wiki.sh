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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/publish-hostess7-wiki.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Publish wiki-hostess7/*.md → github.com/ZacharyGeurts/Hostess7.wiki
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WIKI_SRC="${ROOT}/wiki-hostess7"
WIKI_REPO="${WIKI_REPO:-${ROOT}/.wiki-hostess7-publish}"
WIKI_REMOTE="${WIKI_REMOTE:-git@github.com:ZacharyGeurts/Hostess7.wiki.git}"
H7_SECURE="${ROOT}/Hostess7/scripts/hostess7_secure_git.py"
VER="${HOSTESS7_VERSION:-1.0.0-beta}"
REPO="${HOSTESS7_GITHUB_REPO:-ZacharyGeurts/Hostess7}"

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

_sync_main_repo_wiki() {
  local f dest
  mkdir -p "${ROOT}/dist/hostess7-wiki-sync"
  rsync -a "${WIKI_SRC}/" "${ROOT}/dist/hostess7-wiki-sync/"
  for f in "${WIKI_SRC}"/*.md; do
    [[ -f "$f" ]] || continue
    dest="wiki/$(basename "$f")"
    local sha=""
    sha="$(gh api "repos/${REPO}/contents/${dest}" --jq .sha 2>/dev/null || true)"
    local args=(-f message="wiki: Hostess 7 ${VER} — $(basename "$f")" -f content="$(base64 -w0 "$f")")
    [[ -n "$sha" ]] && args+=(-f sha="$sha")
    gh api -X PUT "repos/${REPO}/contents/${dest}" "${args[@]}" >/dev/null
    echo "  synced main:${dest}"
  done
  echo "Wiki mirror: https://github.com/${REPO}/tree/main/wiki"
}

git -C "$WIKI_REPO" add -A
if ! git -C "$WIKI_REPO" diff --cached --quiet; then
  git -C "$WIKI_REPO" -c user.email="gzac5314@users.noreply.github.com" -c user.name="ZacharyGeurts" \
    commit -m "wiki: Hostess 7 ${VER} — brain · truth · counsel"
fi

if [[ -f "$H7_SECURE" ]]; then
  pythong "$H7_SECURE" verify
  if pythong "$H7_SECURE" push "$WIKI_REPO" --branch master --remote "$WIKI_REMOTE" --force 2>/dev/null \
    || pythong "$H7_SECURE" push "$WIKI_REPO" --branch main --remote "$WIKI_REMOTE" --force 2>/dev/null; then
    echo "Wiki: https://github.com/${REPO}/wiki"
    exit 0
  fi
else
  git -C "$WIKI_REPO" remote set-url origin "$WIKI_REMOTE" 2>/dev/null || git -C "$WIKI_REPO" remote add origin "$WIKI_REMOTE"
fi

if git -C "$WIKI_REPO" push origin master 2>/dev/null \
  || git -C "$WIKI_REPO" push origin main 2>/dev/null \
  || git -C "$WIKI_REPO" push -u origin HEAD 2>/dev/null; then
  echo "Wiki: https://github.com/${REPO}/wiki"
  exit 0
fi

echo "Hostess7.wiki.git not provisioned — syncing wiki/ on main branch" >&2
_sync_main_repo_wiki
echo "" >&2
echo "One-time bootstrap for GitHub Wiki UI:" >&2
echo "  https://github.com/${REPO}/wiki/_new" >&2
echo "  Create Home page (any content), then re-run: bash scripts/publish-hostess7-wiki.sh" >&2