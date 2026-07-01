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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/publish-stack-releases.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Companion releases on stack repos — all point to canonical AmmoOS code + release.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VER="${STACK_VERSION:-2.0.0-beta5}"
TAG="${STACK_TAG:-v${VER}}"
AMMOOS_REPO="${AMMOOS_REPO:-ZacharyGeurts/AmmoOS}"
OWNER="${GITHUB_OWNER:-ZacharyGeurts}"
HUB_JSON="${ROOT}/data/ammoos-pages-hub.json"
NOTES_DIR="${ROOT}/.stack-release-notes"

log() { printf '[stack-release] %s\n' "$*"; }

[[ -f "$HUB_JSON" ]] || { echo "missing $HUB_JSON" >&2; exit 1; }
mkdir -p "$NOTES_DIR"

python3 - <<'PY' "$HUB_JSON" "$VER" "$TAG" "$AMMOOS_REPO" "$NOTES_DIR"
import json, sys
from pathlib import Path

hub_path, ver, tag, ammoos, out_dir = sys.argv[1:6]
hub = json.loads(Path(hub_path).read_text(encoding="utf-8"))
base = hub.get("canonical_base", "https://zacharygeurts.github.io/AmmoOS/").rstrip("/") + "/"
code = hub.get("canonical_repo", f"https://github.com/{ammoos}")
release = f"{code}/releases/tag/{tag}"
for name, entry in sorted((hub.get("repos") or {}).items()):
    if name == "AmmoOS":
        continue
    page = entry.get("ammoos_page", "index.html")
    manual = base + page
    title = entry.get("title", name)
    blurb = entry.get("blurb", "")
    sib = entry.get("github", f"https://github.com/ZacharyGeurts/{name}")
    body = f"""# {title} — AmmoOS {ver} stack companion

**Canonical code:** [{ammoos}]({code})  
**AmmoOS release:** [{tag}]({release})  
**Manual:** [{page}]({manual})

{blurb}

This component ships inside the **AmmoOS** tree. Clone AmmoOS, wire siblings, install:

```bash
git clone {code}.git
cd AmmoOS
git checkout {tag}
./scripts/wire-stack.sh
sudo ./install-all.sh
```

Component repo: [{name}]({sib}) · Pages hub redirects to the AmmoOS manual.
"""
    Path(out_dir, f"{name}.md").write_text(body, encoding="utf-8")
    print(name)
PY

while IFS= read -r name; do
  [[ -n "$name" ]] || continue
  repo="${OWNER}/${name}"
  gh repo view "$repo" >/dev/null 2>&1 || { log "skip $repo (missing)"; continue; }
  notes="${NOTES_DIR}/${name}.md"
  if gh release view "$TAG" -R "$repo" >/dev/null 2>&1; then
    gh release edit "$TAG" -R "$repo" --title "${name} · AmmoOS ${VER}" --notes-file "$notes"
    log "updated $repo $TAG"
  else
    gh release create "$TAG" -R "$repo" --title "${name} · AmmoOS ${VER}" --notes-file "$notes"
    log "created $repo $TAG"
  fi
done < <(python3 - <<'PY' "$HUB_JSON"
import json, sys
from pathlib import Path
hub = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for name in sorted((hub.get("repos") or {}).keys()):
    if name != "AmmoOS":
        print(name)
PY
)

log "done — canonical release: https://github.com/${AMMOOS_REPO}/releases/tag/${TAG}"