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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:AmmoCode/scripts/ammocode-smoke-test.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# AmmoCode NEXUS C2 smoke test — toolbar, themes, settings, static assets
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export SG_ROOT="${SG_ROOT:-$(dirname "$ROOT")}"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$SG_ROOT/AmmoOS}"
export GROK16_ROOT="${GROK16_ROOT:-$ROOT/Grok16}"
PORT="${AMMOCODE_PORT:-19555}"
export AMMOCODE_PORT="$PORT"

fail() { echo "FAIL: $*" >&2; exit 1; }
ok() { echo "OK: $*"; }

cd "$ROOT"

python3 ammocode.py --check >/tmp/ammocode-check.json || fail "ammocode --check"
python3 -c "import json; d=json.load(open('/tmp/ammocode-check.json')); assert d.get('ok')" || fail "check json"

python3 scripts/ammocode-toolbar-icons.py >/tmp/ammocode-icons.log || fail "icon generator"
ICON_COUNT=$(find assets/icons/toolbar -name '*.png' 2>/dev/null | wc -l)
[[ "$ICON_COUNT" -ge 160 ]] || fail "expected 160+ toolbar icons, got $ICON_COUNT"

for f in index.html assets/ammocode-nexus-c2.css assets/ammocode-syntax.css \
  lib/ammocode-app.js lib/ammocode-toolbar.js lib/highlight.js \
  data/ammocode-toolbar-doctrine.json data/ammocode-syntax-themes.json; do
  [[ -f "$f" ]] || fail "missing $f"
done

python3 ammocode.py &
PID=$!
trap 'kill $PID 2>/dev/null || true' EXIT
sleep 1

curl -sf "http://127.0.0.1:$PORT/api/toolbar" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d.get('ok') or d.get('schema')
assert len(d.get('items',[])) >= 40
print('toolbar items:', len(d['items']))
" || fail "/api/toolbar"

curl -sf "http://127.0.0.1:$PORT/api/syntax-themes" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert 'editor_themes' in d and 'syntax_themes' in d
assert 'nexus_c2' in d['editor_themes']
" || fail "/api/syntax-themes"

curl -sf -X POST "http://127.0.0.1:$PORT/api/ammocode" \
  -H 'Content-Type: application/json' \
  -d '{"action":"ping"}' | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert d.get('ok') and d.get('ammocode')
" || fail "ping"

curl -sf "http://127.0.0.1:$PORT/" | grep -q 'ac-nexus-c2' || fail "index shell"

ok "AmmoCode NEXUS C2 smoke test passed ($ICON_COUNT icons)"