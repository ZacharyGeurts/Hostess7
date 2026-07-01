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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/nexus-elevate.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS elevation — UAC-style Allow/Cancel, then OS polkit auth via hardened bridge.
set -euo pipefail

_NEXUS_ELEVATE_LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${_NEXUS_ELEVATE_LIB}/nexus-polkit.sh"

nexus_elevate_has_gui() {
  [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]
}

nexus_elevate_gui_confirm() {
  local title="${1:-NEXUS Field}"
  local body="${2:-Allow NEXUS to install all field systems on this computer?}"
  if ! nexus_elevate_has_gui; then
    return 0
  fi
  if command -v zenity >/dev/null 2>&1; then
    zenity --question --title="$title" --width=420 \
      --text="$body\n\nLike Windows administrator approval — Allow, then authenticate once in the system dialog." \
      --ok-label="Allow" --cancel-label="Cancel" 2>/dev/null
    return $?
  fi
  if command -v kdialog >/dev/null 2>&1; then
    kdialog --title "$title" --yesno "$body" 2>/dev/null
    return $?
  fi
  if command -v yad >/dev/null 2>&1; then
    yad --title "$title" --text "$body" --button="Allow:0" --button="Cancel:1" 2>/dev/null
    return $?
  fi
  return 0
}

nexus_elevate_sudo_keepalive_start() {
  [[ "$(id -u)" -eq 0 ]] && return 0
  [[ -n "${NEXUS_SUDO_KEEPALIVE_PID:-}" ]] && kill -0 "$NEXUS_SUDO_KEEPALIVE_PID" 2>/dev/null && return 0
  (
    while true; do
      sudo -n true 2>/dev/null || exit 0
      sleep 50
      kill -0 "$PPID" 2>/dev/null || exit 0
    done
  ) &
  NEXUS_SUDO_KEEPALIVE_PID=$!
  export NEXUS_SUDO_KEEPALIVE_PID
}

nexus_elevate_sudo_keepalive_stop() {
  [[ -n "${NEXUS_SUDO_KEEPALIVE_PID:-}" ]] && kill "$NEXUS_SUDO_KEEPALIVE_PID" 2>/dev/null || true
}

nexus_elevate_pkexec_install() {
  local script="$1"
  shift || true
  local bridge action
  bridge="$(nexus_polkit_bridge_path)" || return 1
  nexus_polkit_bootstrap_if_cached_sudo
  action="$(nexus_polkit_action_for install)"
  pkexec --action "$action" "$bridge" run-install "$script" "$@"
}

nexus_elevate_run_as_root() {
  local inner="$1"
  if [[ "$(id -u)" -eq 0 ]]; then
    bash -c "$inner"
    return $?
  fi
  if sudo -n true 2>/dev/null; then
    sudo -E bash -c "$inner"
    return $?
  fi
  if command -v pkexec >/dev/null 2>&1 && nexus_elevate_has_gui; then
    local bridge action inner_script state_dir
    bridge="$(nexus_polkit_bridge_path)" || return 1
    nexus_polkit_bootstrap_if_cached_sudo
    action="$(nexus_polkit_action_for update)"
    state_dir="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}"
    mkdir -p "$state_dir" 2>/dev/null || true
    inner_script="${state_dir}/update-elevate-inner.sh"
    {
      printf '%s\n' '#!/bin/bash' 'set -euo pipefail'
      printf '%s\n' "$inner"
    } >"$inner_script"
    chmod 700 "$inner_script"
    pkexec --action "$action" "$bridge" run-update "$inner_script"
    local rc=$?
    rm -f "$inner_script"
    return $rc
  fi
  if command -v zenity >/dev/null 2>&1 && nexus_elevate_has_gui; then
    local pw
    pw="$(zenity --password --title="NEXUS Field — Administrator" \
      --text="Authenticate once to run NEXUS Field administration." 2>/dev/null || true)"
    if [[ -z "$pw" ]]; then
      return 3
    fi
    printf '%s\n' "$pw" | sudo -S -E bash -c "$inner"
    return $?
  fi
  sudo -E bash -c "$inner"
}

# Acquire root for current script — call once at top of installer.
nexus_elevate_acquire() {
  if [[ "$(id -u)" -eq 0 ]]; then
    export NEXUS_ELEVATED_ROOT=1
    return 0
  fi
  if [[ "${NEXUS_ELEVATED_ROOT:-}" == "1" ]]; then
    return 0
  fi
  if sudo -n true 2>/dev/null; then
    export NEXUS_ELEVATED_ROOT=1
    exec sudo -E bash "$@"
  fi
  nexus_elevate_gui_confirm "NEXUS Field Install" \
    "NEXUS Field needs administrator access to install:\n• NEXUS shield + panel\n• Hooks + native layer + CPU shield\n• Firewall + systemd service\n• Start menu shortcut" || {
    echo "Install cancelled." >&2
    exit 3
  }
  if command -v pkexec >/dev/null 2>&1 && nexus_elevate_has_gui; then
    export NEXUS_ELEVATED_ROOT=1
    local target installer
    target="${1:-}"
    shift || true
    installer="$(readlink -f "$target" 2>/dev/null || true)"
    [[ -n "$installer" && -f "$installer" ]] || installer="$(nexus_polkit_resolve_installer install-all.sh)" || {
      echo "Installer script not found." >&2
      exit 2
    }
    exec nexus_elevate_pkexec_install "$installer" "$@"
  fi
  echo "Administrator authentication required (once)…"
  sudo -v || exit 1
  nexus_elevate_sudo_keepalive_start
  export NEXUS_ELEVATED_ROOT=1
  exec sudo -E bash "$@"
}