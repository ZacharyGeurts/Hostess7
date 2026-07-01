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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/sg-code-open.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Open any programming file — Run G16 · Compile · AmmoCode (stack default).
set -euo pipefail

FILE="${1:-}"
[[ -n "$FILE" && -f "$FILE" ]] || {
  echo "usage: sg-code-open.sh <source-file>" >&2
  exit 1
}

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
source "${ROOT}/lib/sg-paths.sh"
sg_paths_export_defaults

PY="${PYTHONG:-$(command -v pythong || command -v python3)}"
FT="${ROOT}/lib/field-programming-filetypes.py"
OPEN="${ROOT}/scripts/integrate-ammocode.sh"
AMMOCODE_OPEN="${AMMOCODE_ROOT:-${ROOT}/AmmoCode}/scripts/ammocode-open.sh"
PORT="${AMMOCODE_PORT:-9555}"
DEFAULT="${SG_CODE_DEFAULT:-ask}"

abs="$(cd "$(dirname "$FILE")" && pwd)/$(basename "$FILE")"
log() { printf '[sg-code-open] %s\n' "$*"; }

# Special handlers (.comp / .spv → AMOURANTHRTX)
handler="$("$PY" "$FT" discern "$abs" 2>/dev/null || echo "")"
special="$("$PY" -c "
import json,sys
from pathlib import Path
import importlib.util
spec=importlib.util.spec_from_file_location('ft','$FT')
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
h=m.special_handler('$abs')
print(h or '')
" 2>/dev/null || true)"
if [[ -n "$special" && -x "$special" ]]; then
  log "special → $special"
  exec "$special" "$abs"
fi

pick="${SG_CODE_ACTION:-}"
if [[ -z "$pick" && "$DEFAULT" == "ask" ]] && command -v zenity >/dev/null 2>&1; then
  pick="$(zenity --list --title="SG Code — $(basename "$abs")" \
    --text="Language: ${handler:-unknown}\nChoose action:" \
    --column="Action" --column="Description" \
    "edit" "Open in AmmoCode" \
    "run" "Run with G16" \
    "compile" "Compile with G16" \
    --height=260 --width=420 2>/dev/null || true)"
fi
[[ -z "$pick" ]] && pick="${DEFAULT:-edit}"
[[ "$pick" == "ask" || -z "$pick" ]] && pick="edit"

case "$pick" in
  run)
    log "run g16 → $abs"
    exec "$PY" "$FT" run "$abs"
    ;;
  compile)
    log "compile g16 → $abs"
    exec "$PY" "$FT" compile "$abs"
    ;;
  edit|ammocode|*)
    if [[ -x "$AMMOCODE_OPEN" ]]; then
      exec "$AMMOCODE_OPEN" "$abs"
    fi
    url="http://127.0.0.1:${PORT}/?file=$(python3 -c "import urllib.parse; print(urllib.parse.quote('''$abs'''))")"
    log "AmmoCode → $url"
    if ! curl -sf "http://127.0.0.1:${PORT}/api/ammocode" -X POST -H 'Content-Type: application/json' -d '{"action":"ping"}' >/dev/null 2>&1; then
      (cd "${AMMOCODE_ROOT:-${ROOT}/AmmoCode}" && nohup python3 ammocode.py >/dev/null 2>&1 &)
      sleep 1
    fi
    if command -v xdg-open >/dev/null 2>&1; then
      exec xdg-open "$url"
    fi
    echo "$url"
    ;;
esac