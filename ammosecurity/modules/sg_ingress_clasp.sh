#!/usr/bin/env bash
# ingress_clasp — extra clasp over USB, Bluetooth, WiFi, NFC, WWAN, Thunderbolt
# Master ingress lock. Use -Unlock to release (requires root).
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/common.sh"

CLASP_STATE='/var/lib/ammo/ingress-clasp.lock'
CLASP_UDEV='/etc/udev/rules.d/99-ammo-ingress-clasp.rules'
CLASP_MODPROBE='/etc/modprobe.d/ammo-ingress-clasp.conf'

cmd_clasp_install_rules() {
  ammo_sudo mkdir -p /var/lib/ammo 2>/dev/null || true

  ammo_log 'clasp udev — deny all new USB hotplug'
  ammo_sudo tee "$CLASP_UDEV" >/dev/null <<'EOF'
# ammosecurity ingress clasp — extra lock on USB/BT/WiFi ingress vectors
# Block NEW usb devices (already-authorized boot devices stay until re-clasp)
ACTION=="add", SUBSYSTEM=="usb", ENV{DEVTYPE}=="usb_device", \
  TEST=="authorized", ATTR{authorized}="0", ENV{AMMO_CLASP}="usb_denied"

# Block NEW sd/usb-storage sticks
ACTION=="add", SUBSYSTEM=="block", KERNEL=="sd[a-z]", ENV{ID_BUS}=="usb", \
  RUN+="/bin/sh -c 'echo 0 > /sys/block/%k/device/authorized 2>/dev/null || blockdev --setro /dev/%k 2>/dev/null || true'"

# Reject new bluetooth hci adapters
ACTION=="add", SUBSYSTEM=="bluetooth", RUN+="/bin/sh -c 'rfkill block bluetooth 2>/dev/null || true'"
EOF
  ammo_sudo udevadm control --reload-rules 2>/dev/null || true

  ammo_log 'clasp modprobe — blacklist wireless + BT USB + mass storage'
  ammo_sudo tee "$CLASP_MODPROBE" >/dev/null <<'EOF'
# ammosecurity ingress clasp — kernel-level ingress deny
blacklist btusb
blacklist btbcm
blacklist btrtl
blacklist btintel
blacklist uvcvideo
blacklist snd_usb_audio
blacklist usb_storage
blacklist uas
blacklist thunderbolt
blacklist iwlmvm
blacklist iwlwifi
blacklist ath10k_pci
blacklist ath11k_pci
blacklist brcmfmac
blacklist rtw88_*
blacklist rtw89_*
blacklist mt76x2u
install btusb /bin/false
install usb_storage /bin/false
install thunderbolt /bin/false
EOF
}

cmd_clasp_usb() {
  ammo_log 'USB clasp — deauthorize unknown devices, lock storage'
  ammo_sudo sysctl -w kernel.modules_disabled=0 2>/dev/null || true

  local path
  for path in /sys/bus/usb/devices/usb*/authorized_default; do
    [[ -f "$path" ]] && echo 0 2>/dev/null | ammo_sudo tee "$path" >/dev/null || true
  done

  for path in /sys/bus/usb/devices/[0-9]*; do
    [[ -d "$path" ]] || continue
    [[ -f "$path/authorized" ]] || continue
    # Keep root hubs (device 1); clasp everything else not already boot-critical
    local dev
    dev="$(basename "$path")"
    if [[ "$dev" != "1"* ]] && [[ -f "$path/idVendor" ]]; then
      echo 0 2>/dev/null | ammo_sudo tee "$path/authorized" >/dev/null || true
    fi
  done

  ammo_sudo modprobe -r usb_storage uas 2>/dev/null || true
  ammo_log 'USB clasp engaged — no new sticks, no rogue HID hotplug'
}

cmd_clasp_bluetooth() {
  ammo_log 'Bluetooth clasp'
  ammo_service_off bluetooth
  ammo_service_off bluetooth.target
  if command -v rfkill >/dev/null 2>&1; then
    rfkill list bluetooth 2>/dev/null | awk '/^[0-9]+:/{print $1}' | tr -d ':' | while read -r idx; do
      [[ -n "$idx" ]] && ammo_sudo rfkill block "$idx" 2>/dev/null || true
    done
  fi
  ammo_sudo modprobe -r btusb btbcm btrtl btintel 2>/dev/null || true
  ammo_log 'Bluetooth clasp engaged'
}

cmd_clasp_wifi() {
  ammo_log 'WiFi clasp — radio off, interfaces down'
  if command -v nmcli >/dev/null 2>&1; then
    ammo_sudo nmcli radio wifi off 2>/dev/null || true
  fi
  if command -v rfkill >/dev/null 2>&1; then
    rfkill list wifi 2>/dev/null | awk '/^[0-9]+:/{print $1}' | tr -d ':' | while read -r idx; do
      [[ -n "$idx" ]] && ammo_sudo rfkill block "$idx" 2>/dev/null || true
    done
    rfkill list wlan 2>/dev/null | awk '/^[0-9]+:/{print $1}' | tr -d ':' | while read -r idx; do
      [[ -n "$idx" ]] && ammo_sudo rfkill block "$idx" 2>/dev/null || true
    done
  fi
  for iface in /sys/class/net/wl* /sys/class/net/wlan*; do
    [[ -e "$iface" ]] || continue
    local name
    name="$(basename "$iface")"
    ammo_sudo ip link set "$name" down 2>/dev/null || true
    ammo_log "wifi iface down: $name"
  done
  ammo_sudo systemctl stop wpa_supplicant@*.service wpa_supplicant.service 2>/dev/null || true
  ammo_sudo modprobe -r iwlwifi ath10k_pci brcmfmac 2>/dev/null || true
  ammo_log 'WiFi clasp engaged — ethernet outbound only'
}

cmd_clasp_other() {
  ammo_log 'NFC / WWAN / Thunderbolt clasp'
  if command -v rfkill >/dev/null 2>&1; then
    for kind in nfc wwan; do
      rfkill list "$kind" 2>/dev/null | awk '/^[0-9]+:/{print $1}' | tr -d ':' | while read -r idx; do
        [[ -n "$idx" ]] && ammo_sudo rfkill block "$idx" 2>/dev/null || true
      done
    done
  fi
  ammo_sudo modprobe -r thunderbolt 2>/dev/null || true
  ammo_service_off ModemManager
}

cmd_clasp_status() {
  ammo_log 'ingress clasp status'
  [[ -f "$CLASP_STATE" ]] && cat "$CLASP_STATE" || echo 'clasp: not locked'
  command -v rfkill >/dev/null && rfkill list 2>/dev/null | grep -E 'Soft blocked: yes|Hard blocked: yes' || true
  ip link show 2>/dev/null | grep -E 'wl|wlan' || echo 'no wifi ifaces up'
  lsusb 2>/dev/null | head -8 || true
}

cmd_clasp_unlock() {
  ammo_log 'UNLOCK ingress clasp — re-enabling USB/BT/WiFi (admin only)'
  ammo_sudo rm -f "$CLASP_UDEV" "$CLASP_MODPROBE" "$CLASP_STATE" 2>/dev/null || true
  ammo_sudo udevadm control --reload-rules 2>/dev/null || true
  for path in /sys/bus/usb/devices/usb*/authorized_default; do
    [[ -f "$path" ]] && echo 1 2>/dev/null | ammo_sudo tee "$path" >/dev/null || true
  done
  if command -v rfkill >/dev/null 2>&1; then
    ammo_sudo rfkill unblock all 2>/dev/null || true
  fi
  if command -v nmcli >/dev/null 2>&1; then
    ammo_sudo nmcli radio wifi on 2>/dev/null || true
    ammo_sudo nmcli radio wwan on 2>/dev/null || true
  fi
  ammo_log 'clasp released — reboot recommended for full driver restore'
}

cmd_ingress_clasp() {
  local mode="${1:-lock}"
  if [[ "$mode" == '-Unlock' || "$mode" == 'unlock' ]]; then
    cmd_clasp_unlock
    return 0
  fi
  if [[ "$mode" == 'status' ]]; then
    cmd_clasp_status
    return 0
  fi

  ammo_log '=== INGRESS CLASP — USB · Bluetooth · WiFi · NFC · WWAN ==='
  cmd_clasp_install_rules
  cmd_clasp_usb
  cmd_clasp_bluetooth
  cmd_clasp_wifi
  cmd_clasp_other
  date -Is 2>/dev/null | ammo_sudo tee "$CLASP_STATE" >/dev/null || ammo_sudo sh -c "date > $CLASP_STATE"
  ammo_log 'ingress clasp LOCKED — use: sg_build.sh -Action Clasp -Unlock to release'
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  cmd_ingress_clasp "${1:-lock}"
fi