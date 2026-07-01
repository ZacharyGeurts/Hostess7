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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-underlay-switch.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Field underlay switch — Tristate installer hooks + F9 hotkey service.
set -euo pipefail

nexus_underlay_switch_board() {
  [[ "${NEXUS_FIELD_UNDERLAY:-1}" == "1" ]] || return 0
  local root="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  local py="${root}/lib/field-underlay-switch.py"
  [[ -f "$py" ]] || return 0
  NEXUS_INSTALL_ROOT="${root}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}" \
    SG_ROOT="${SG_ROOT:-}" KILROY_ROOT="${KILROY_ROOT:-}" \
    pythong "$py" board 2>/dev/null || true
}

nexus_underlay_hotkey_install() {
  local root="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  local user="${1:-${SUDO_USER:-$USER}}"
  local home py
  [[ -f "${root}/lib/field-underlay-hotkey.py" ]] || return 0
  home="$(getent passwd "$user" 2>/dev/null | cut -d: -f6)"
  [[ -n "$home" ]] || home="${HOME:-/home/$user}"
  py="${root}/lib/field-underlay-hotkey.py"
  local autostart="${home}/.config/autostart"
  mkdir -p "$autostart" 2>/dev/null || return 0
  cat >"${autostart}/nexus-underlay-hotkey.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=NEXUS Underlay Hotkey (F9)
Comment=F9 — Tristate installer until defield clean; Queen sovereign browser after secure network
Exec=env NEXUS_INSTALL_ROOT=${root} NEXUS_STATE_DIR=${NEXUS_STATE_DIR:-/var/lib/nexus-shield} pythong ${py}
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
EOF
  chown "${user}:${user}" "${autostart}/nexus-underlay-hotkey.desktop" 2>/dev/null || true
  chmod 644 "${autostart}/nexus-underlay-hotkey.desktop" 2>/dev/null || true
}

nexus_tristate_installer_url() {
  local port="${NEXUS_THREAT_PANEL_PORT:-9477}"
  printf 'http://127.0.0.1:%s/tristate-installer' "$port"
}