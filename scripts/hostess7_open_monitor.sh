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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:Hostess7/scripts/hostess7_open_monitor.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Pop Hostess7 Monitor in a new terminal window.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MONITOR="$ROOT/Hostess7Monitor.sh"
TITLE="Hostess 7 Monitor"

if [[ ! -x "$MONITOR" ]]; then
    echo "BLOCKER: Hostess7Monitor.sh missing" >&2
    exit 1
fi

# gnome-terminal/GTK probe AT-SPI; as root/sudo that hits /root/.cache/at-spi (permission denied).
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

_monitor_inner() {
    cd "$ROOT"
    export NO_AT_BRIDGE=1 GTK_A11Y=none
    exec ./Hostess7Monitor.sh
}

_run() {
    _prepare_gui_env
    _monitor_inner
}

_cmd() {
    printf '%q ' env NO_AT_BRIDGE=1 GTK_A11Y=none bash -lc "cd '$ROOT' && ./Hostess7Monitor.sh"
}

if [[ "${1:-}" == "--print-cmd" ]]; then
    _cmd
    exit 0
fi

_prepare_gui_env

if command -v gnome-terminal >/dev/null 2>&1; then
    NO_AT_BRIDGE=1 GTK_A11Y=none gnome-terminal --window --title="$TITLE" -- bash -lc \
        "export NO_AT_BRIDGE=1 GTK_A11Y=none; cd '$ROOT' && ./Hostess7Monitor.sh; exec bash" \
        2>/dev/null || \
    gnome-terminal --window --title="$TITLE" -- bash -lc \
        "export NO_AT_BRIDGE=1 GTK_A11Y=none; cd '$ROOT' && ./Hostess7Monitor.sh; exec bash"
elif command -v kitty >/dev/null 2>&1; then
    kitty --title "$TITLE" bash -lc "export NO_AT_BRIDGE=1 GTK_A11Y=none; cd '$ROOT' && ./Hostess7Monitor.sh; exec bash" &
elif command -v alacritty >/dev/null 2>&1; then
    alacritty --title "$TITLE" -e bash -lc "export NO_AT_BRIDGE=1 GTK_A11Y=none; cd '$ROOT' && ./Hostess7Monitor.sh; exec bash" &
elif command -v xfce4-terminal >/dev/null 2>&1; then
    xfce4-terminal --title="$TITLE" -e bash -lc "export NO_AT_BRIDGE=1 GTK_A11Y=none; cd '$ROOT' && ./Hostess7Monitor.sh; exec bash"
elif command -v konsole >/dev/null 2>&1; then
    konsole --new-tab -p tabtitle="$TITLE" -e bash -lc "export NO_AT_BRIDGE=1 GTK_A11Y=none; cd '$ROOT' && ./Hostess7Monitor.sh; exec bash"
elif command -v xterm >/dev/null 2>&1; then
    xterm -T "$TITLE" -e bash -lc "export NO_AT_BRIDGE=1 GTK_A11Y=none; cd '$ROOT' && ./Hostess7Monitor.sh" &
elif command -v x-terminal-emulator >/dev/null 2>&1; then
    x-terminal-emulator -T "$TITLE" -e bash -lc "export NO_AT_BRIDGE=1 GTK_A11Y=none; cd '$ROOT' && ./Hostess7Monitor.sh; exec bash"
else
    echo "No GUI terminal found. Open a second window and run:" >&2
    echo "  cd '$ROOT' && ./Hostess7Monitor.sh" >&2
    exit 1
fi