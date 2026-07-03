#!/usr/bin/env bash
# service_cleaner — stop, disable, and mask leaky or hostile services
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/common.sh"

JUNK_UNITS=(
  telnet.socket inetd openbsd-inetd
  vsftpd proftpd pure-ftpd
  rsh.socket rlogin.socket rexec.socket
  smbd nmbd smb winbind
  avahi-daemon avahi-daemon.socket
  cups-browsed cups.socket
  whoopsie apport
  hostapd create_ap dnsmasq
  bluetooth bluetooth.service bluetooth.target
  rpcbind nfs-server nfs-kernel-server
  snapd snapd.socket
  teamviewerd anydesk
  clamav-freshclam clamav-daemon clamav-daemon.socket
  fail2ban ufw
  unattended-upgrades
)

JUNK_USER_UNITS=(
  copyq parcellite clipit greenclip diodon klipper
)

cmd_service_cleaner() {
  ammo_log 'service cleaner — disabling hostile/leaky units'

  for unit in "${JUNK_UNITS[@]}"; do
    if systemctl list-unit-files "$unit" &>/dev/null || systemctl status "$unit" &>/dev/null; then
      ammo_service_off "$unit"
      ammo_log "system: masked $unit"
    fi
  done

  for unit in "${JUNK_USER_UNITS[@]}"; do
    systemctl --user stop "$unit" 2>/dev/null || true
    systemctl --user mask "$unit" 2>/dev/null || true
    systemctl --user disable "$unit" 2>/dev/null || true
  done

  local autostart="${HOME}/.config/autostart"
  if [[ -d "$autostart" ]]; then
    find "$autostart" -maxdepth 1 -type f \( -iname '*keylog*' -o -iname '*macro*' -o -iname '*recorder*' \) \
      -print -delete 2>/dev/null || true
  fi

  ammo_log 'still-enabled services (review manually):'
  systemctl list-unit-files --state=enabled --no-pager 2>/dev/null \
    | grep -E 'telnet|ftp|rsh|smb|avahi|bluetooth|hostapd|rpcbind|nfs' \
    || ammo_log 'no obvious junk still enabled'
  ammo_health_note 'service_cleaner applied'
}

cmd_status() {
  ammo_log '=== service cleaner status ==='
  local bad=0
  for unit in smbd avahi-daemon ufw bluetooth; do
    if systemctl is-active "$unit" &>/dev/null; then
      echo "ACTIVE: $unit"
      bad=1
    fi
  done
  [[ "$bad" -eq 0 ]] && echo 'no obvious junk services active'
  ammo_health_note 'service_cleaner status'
}

cmd_drift_check() {
  local drift=0
  for unit in smbd nmbd ufw avahi-daemon; do
    if systemctl is-active "$unit" &>/dev/null; then
      ammo_violation "service drift: $unit active"
      drift=1
    fi
  done
  return "$drift"
}

main() {
  case "${1:-apply}" in
    status) cmd_status ;;
    drift) cmd_drift_check ;;
    dry-run|test) cmd_status ;;
    *) cmd_service_cleaner ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi