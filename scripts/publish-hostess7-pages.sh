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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/publish-hostess7-pages.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Publish Hostess7/docs (boot terminal only) → GitHub Pages gh-pages branch.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DOCS_SRC="${ROOT}/Hostess7/docs"
PAGES_REPO="${PAGES_REPO:-${ROOT}/.pages-hostess7-publish}"
PAGES_REMOTE="${PAGES_REMOTE:-git@github.com:ZacharyGeurts/Hostess7.git}"
PAGES_BRANCH="${PAGES_BRANCH:-gh-pages}"
HOSTESS7_VERSION="${HOSTESS7_VERSION:-1.0.0-beta}"
OWNER="${GITHUB_PAGES_OWNER:-ZacharyGeurts}"

log() { printf '[hostess7-pages] %s\n' "$*"; }

[[ -d "$DOCS_SRC" ]] || { echo "Missing ${DOCS_SRC}" >&2; exit 1; }

# Refresh machine-readable status before publish (pages-boot — not demo)
if [[ -f "${DOCS_SRC}/status.json" ]]; then
  python3 - <<'PY' "${DOCS_SRC}/status.json" "$HOSTESS7_VERSION"
import json, sys
from datetime import datetime, timezone
path, ver = sys.argv[1], sys.argv[2]
doc = json.load(open(path))
doc.update({
    "version": ver,
    "mode": "pages-boot-terminal",
    "pages_role": "boot_terminal_only",
    "live_surfaces": "127.0.0.1 loopback — not github.io",
    "posture": "war-ready",
    "war_ready": True,
    "demo": False,
    "brain": False,
    "boot_command": "./Hostess7.sh boot",
    "pages_url": "https://zacharygeurts.github.io/Hostess7/",
    "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
})
json.dump(doc, open(path, "w"), indent=2)
print("status.json refreshed (pages-boot-terminal)")
PY
fi

H7_SECURE="${ROOT}/Hostess7/scripts/hostess7_secure_git.py"

log "stage docs → ${PAGES_REPO} (${PAGES_BRANCH})"
if [[ ! -d "${PAGES_REPO}/.git" ]]; then
  rm -rf "$PAGES_REPO"
  if [[ -f "$H7_SECURE" ]]; then
    pythong "$H7_SECURE" verify
    if ! pythong "$H7_SECURE" clone "$PAGES_REPO" --remote "$PAGES_REMOTE" --branch "$PAGES_BRANCH" 2>/dev/null; then
      mkdir -p "$PAGES_REPO"
      git -C "$PAGES_REPO" init -b "$PAGES_BRANCH"
      git -C "$PAGES_REPO" remote add origin "$PAGES_REMOTE"
    fi
  else
    mkdir -p "$PAGES_REPO"
    git -C "$PAGES_REPO" init -b "$PAGES_BRANCH"
    git -C "$PAGES_REPO" remote add origin "$PAGES_REMOTE"
  fi
fi

rsync -a --delete \
  --exclude='.git' \
  "${DOCS_SRC}/" "${PAGES_REPO}/"

cd "$PAGES_REPO"
git add -A
if git diff --cached --quiet; then
  log "GitHub Pages already up to date"
else
  git -c user.email="gzac5314@users.noreply.github.com" -c user.name="ZacharyGeurts" \
    commit -m "pages: Hostess7 boot terminal v${HOSTESS7_VERSION}"
  H7_SECURE="${ROOT}/Hostess7/scripts/hostess7_secure_git.py"
  if [[ -f "$H7_SECURE" ]]; then
    pythong "$H7_SECURE" push "$PAGES_REPO" --branch "$PAGES_BRANCH" \
      --remote "git@github.com:ZacharyGeurts/Hostess7.git" --force
  else
    git push origin "$PAGES_BRANCH" 2>/dev/null || git push -u origin "$PAGES_BRANCH"
  fi
  log "pushed gh-pages"
fi

# Ensure GitHub Pages source is gh-pages / root
if gh api "repos/${OWNER}/Hostess7/pages" --jq '.source.branch' 2>/dev/null | grep -q gh-pages; then
  log "Pages source already gh-pages"
else
  gh api -X POST "repos/${OWNER}/Hostess7/pages" \
    -f build_type=legacy \
    -f source[branch]=gh-pages \
    -f source[path]=/ 2>/dev/null \
    || gh api -X PUT "repos/${OWNER}/Hostess7/pages" \
      -f build_type=legacy \
      -f source[branch]=gh-pages \
      -f source[path]=/ 2>/dev/null \
    || log "WARN configure Pages in repo Settings if needed"
fi

log "live → https://zacharygeurts.github.io/Hostess7/"