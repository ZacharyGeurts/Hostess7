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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/device-whitelist.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# AMOURANTHRTX field learnings — whitelist common devices and consumer processes.
# AMOURANTHRTX: GPL v3 or commercial (not MIT-free). NEXUS-Shield: MIT.

NEXUS_DEVICE_WHITELIST_COMM=(
  systemd
  systemd-logind
  dbus-daemon
  pipewire
  pipewire-pulse
  pulseaudio
  wireplumber
  bluetoothd
  NetworkManager
  wpa_supplicant
  Xorg
  Xwayland
  gnome-shell
  kwin_x11
  kwin_wayland
  sway
  hyprland
  firefox
  chrome
  chromium
  google-chrome
  google-chrome-stable
  brave
  brave-browser
  thunderbird
  betterbird
  evolution
  geary
  mailspring
  slack
  zoom
  teams
  code
  cursor
  steam
  gamemoded
  cupsd
  colord
  udisksd
  upowerd
  ModemManager
  containerd
  dockerd
  nexus-daemon
)

nexus_device_whitelist_load() {
  if [[ -f "${NEXUS_INSTALL_ROOT}/config/device-whitelist.conf" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/config/device-whitelist.conf"
  fi
}

nexus_is_whitelisted_process() {
  local comm="${1:-}"
  local exe="${2:-}"
  nexus_device_whitelist_load
  local allowed
  for allowed in "${NEXUS_DEVICE_WHITELIST_COMM[@]}"; do
    [[ "$comm" == "$allowed" ]] && return 0
  done
  case "$exe" in
    /usr/bin/*|/usr/lib/*|/usr/libexec/*|/opt/*) return 0 ;;
  esac
  case "$comm" in
    nexus-*|stealth_*) return 0 ;;
  esac
  return 1
}

nexus_is_whitelisted_device_path() {
  local path="${1:-}"
  case "$path" in
    /dev/input/*|/dev/snd/*|/dev/dri/*|/dev/video*|/dev/tty*|/dev/usb/*|/dev/bus/usb/*) return 0 ;;
    /run/udev/*|/sys/class/input/*|/sys/class/sound/*) return 0 ;;
  esac
  return 1
}