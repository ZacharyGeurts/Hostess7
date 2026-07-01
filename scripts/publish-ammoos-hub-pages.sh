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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/publish-ammoos-hub-pages.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Publish thin Pages stubs for stack repos — link to AmmoOS code + manual.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VER="${AMMOOS_VERSION:-2.0.0-beta5}"
STAGE="${ROOT}/.pages-hub-staging"
HUB_PY="${ROOT}/lib/page_ammoos_hub.py"
OWNER="${GITHUB_PAGES_OWNER:-ZacharyGeurts}"

log() { printf '[hub-pages] %s\n' "$*"; }

[[ -f "$HUB_PY" ]] || { echo "missing page_ammoos_hub.py" >&2; exit 1; }

if [[ -f "${ROOT}/docs/build-ammoos-manual.py" ]]; then
  python3 "${ROOT}/docs/build-ammoos-manual.py"
fi

pages_source() {
  local repo="$1"
  local branch path
  branch="$(gh api "repos/${OWNER}/${repo}/pages" --jq '.source.branch // empty' 2>/dev/null || true)"
  if [[ -n "$branch" ]]; then
    path="$(gh api "repos/${OWNER}/${repo}/pages" --jq '.source.path // "/"' 2>/dev/null || echo "/")"
    path="${path#/}"
    printf '%s\t%s\n' "$branch" "$path"
  else
    echo -e "main\tdocs"
  fi
}

publish_one() {
  local name="$1" manual_url="$2"
  local remote="https://github.com/${OWNER}/${name}.git"
  local repo_dir="${ROOT}/.pages-hub-${name}"
  local branch path rel_path

  log "${name} → ${manual_url}"
  gh repo view "${OWNER}/${name}" >/dev/null 2>&1 || { log "skip ${name} (missing)"; return 0; }

  rm -rf "${STAGE:?}/${name}"
  python3 "$HUB_PY" --out "$STAGE" --version "$VER" --repo "$name" >/dev/null

  IFS=$'\t' read -r branch path < <(pages_source "$name")
  branch="${branch:-gh-pages}"
  path="${path:-/}"
  path="${path#/}"
  path="${path%/}"

  rm -rf "$repo_dir"
  if git ls-remote --heads "$remote" "$branch" 2>/dev/null | grep -q "$branch"; then
    git clone --branch "$branch" --single-branch "$remote" "$repo_dir"
  else
    mkdir -p "$repo_dir"
    git -C "$repo_dir" init -b "$branch"
    git -C "$repo_dir" remote add origin "$remote"
  fi
  [[ -d "${repo_dir}/.git" ]] || { log "FAIL ${name} — no .git"; return 0; }

  if [[ -n "$path" && "$path" != "." ]]; then
    mkdir -p "${repo_dir}/${path}"
    cp "${STAGE}/${name}/index.html" "${repo_dir}/${path}/index.html"
    rel_path="${path}/index.html"
  else
    rsync -a --delete --exclude='.git' "${STAGE}/${name}/" "${repo_dir}/"
    rel_path="index.html"
  fi

  git -C "$repo_dir" add -A
  if git -C "$repo_dir" diff --cached --quiet; then
    log "${name} up to date (${branch}/${path:-/})"
    return 0
  fi
  git -C "$repo_dir" -c user.email="gzac5314@users.noreply.github.com" -c user.name="ZacharyGeurts" \
    commit -m "pages: ${name} hub → AmmoOS code + manual v${VER}"
  git -C "$repo_dir" push origin "$branch"
  log "published ${branch}/${rel_path} → https://${OWNER,,}.github.io/${name}/"
}

while IFS=$'\t' read -r name manual_url; do
  [[ -n "$name" ]] || continue
  [[ "$name" == "AmmoOS" ]] && continue
  publish_one "$name" "$manual_url" || log "WARN ${name} publish partial"
done < <(python3 "$HUB_PY" --out "$STAGE" --version "$VER" --list)

log "done — canonical code: https://github.com/ZacharyGeurts/AmmoOS"