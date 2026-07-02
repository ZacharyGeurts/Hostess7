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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:Hostess7/scripts/hostess7_open_graphics.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Pop Hostess7 Graphics window (GTK pixel canvas — not ASCII).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GFX="$ROOT/scripts/hostess7_gfx_window.py"
TITLE="Hostess 7 Graphics"

_prepare_gui_env() {
    export NO_AT_BRIDGE=1
    export GTK_A11Y=none
    if [[ -n "${SUDO_USER:-}" && "$(id -u)" -eq 0 ]]; then
        local uid home runtime
        uid="$(id -u "$SUDO_USER" 2>/dev/null || true)"
        home="$(getent passwd "$SUDO_USER" 2>/dev/null | cut -d: -f6 || true)"
        if [[ -n "$uid" && -n "$home" ]]; then
            export HOME="$home"
            export USER="$SUDO_USER"
            export LOGNAME="$SUDO_USER"
            runtime="/run/user/$uid"
            if [[ -d "$runtime" ]]; then
                export XDG_RUNTIME_DIR="$runtime"
                export DBUS_SESSION_BUS_ADDRESS="unix:path=${runtime}/bus"
            fi
        fi
    fi
}

if [[ ! -f "$GFX" ]]; then
    echo "BLOCKER: hostess7_gfx_window.py missing" >&2
    exit 1
fi

_prepare_gui_env

if pgrep -f "hostess7_gfx_window.py" >/dev/null 2>&1; then
    echo "Hostess7 Graphics window already running"
    exit 0
fi

nohup env NO_AT_BRIDGE=1 GTK_A11Y=none pythong "$GFX" >/dev/null 2>&1 &
sleep 0.4
echo "Hostess7 Graphics window started (pid background)"
exit 0