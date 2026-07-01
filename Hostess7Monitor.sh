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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:Hostess7/Hostess7Monitor.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Hostess 7 Monitor — live brain map + learning feed (second terminal window)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export HOSTESS7_ROOT="$ROOT"
export NO_AT_BRIDGE="${NO_AT_BRIDGE:-1}"
export GTK_A11Y="${GTK_A11Y:-none}"

usage() {
    cat <<'EOF'
Hostess 7 Monitor — look in while Hostess7 runs

  ./Hostess7Monitor.sh           Live brain map + learning feed (q quit)
  ./Hostess7Monitor.sh --once    Snapshot text (no TUI)
  ./Hostess7Monitor.sh --popup   Open this monitor in a new terminal

Run Hostess7 first:  ./Hostess7.sh
Monitor opens automatically unless HOSTESS7_MONITOR_POPUP=0
EOF
}

case "${1:-}" in
    -h|--help|help) usage ;;
    --popup|--detach)
        exec "$ROOT/scripts/hostess7_open_monitor.sh"
        ;;
    --once)
        exec pythong "$ROOT/scripts/hostess7_monitor.py" --once
        ;;
    *)
        exec pythong "$ROOT/scripts/hostess7_monitor.py" "$@"
        ;;
esac