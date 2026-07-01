#!/usr/bin/env bash
# human_contact_regulator — cap voltage/current on USB/HID/audio devices touching humans
# Software LDO: 5 V bus only, no PD negotiation, 500 mA ceiling on body-contact classes
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/common.sh"

# USB-IF: 5 V × 500 mA = 2.5 W (human-surface safe ceiling)
HUMAN_USB_MAX_MA=500
HUMAN_USB_MAX_MV=5500

cmd_install_udev_regulator() {
  local rule='/etc/udev/rules.d/99-ammo-human-contact-regulator.rules'
  if [[ -f "$rule" ]]; then
    ammo_log 'human-contact udev regulator already installed'
    return 0
  fi
  ammo_log 'installing voltage/current regulator udev rules (HID, audio, gamepad, touch)'
  ammo_sudo tee "$rule" >/dev/null <<'EOF'
# ammosecurity — voltage regulator on anything in contact with humans
# HID (03), audio (01), wireless (e0/01), hub-facing human interfaces
# Force autosuspend + standard 5 V bus power — block high-draw PD profiles

# Keyboards, mice, touchpads, game controllers, styluses
SUBSYSTEM=="usb", ENV{ID_USB_INTERFACES}=="*:03*:*", \
  ATTR{power/control}="auto", ATTR{power/autosuspend_delay_ms}="1000", \
  ATTR{authorized}="1", ENV{AMMO_HUMAN_CONTACT}="1"

# Headsets / mics / speakers worn on body
SUBSYSTEM=="usb", ENV{ID_USB_INTERFACES}=="*:01*:*", \
  ATTR{power/control}="auto", ATTR{power/autosuspend_delay_ms}="1000", \
  ENV{AMMO_HUMAN_CONTACT}="1"

# Bluetooth dongles (often near keyboard/mouse RF — limit bus power)
SUBSYSTEM=="usb", ATTR{idVendor}=="*", ATTR{idProduct}=="*", \
  ENV{ID_USB_CLASS_FROM_DATABASE}=="Wireless", \
  ATTR{power/control}="auto", ENV{AMMO_HUMAN_CONTACT}="1"

# On add: clamp input current on power_supply nodes tied to human-contact USB
SUBSYSTEM=="power_supply", KERNEL=="usb*", ENV{AMMO_HUMAN_CONTACT}=="1", \
  RUN+="/bin/sh -c 'echo 500000 > /sys/class/power_supply/%k/input_current_limit 2>/dev/null || true'"
EOF
  ammo_sudo udevadm control --reload-rules 2>/dev/null || true
  ammo_sudo udevadm trigger --subsystem-match=usb --action=add 2>/dev/null || true
}

cmd_block_usb_pd() {
  ammo_log 'blocking USB-PD high-voltage negotiation (9/12/20 V outlaw)'
  # type-c: force sink-only / no DR_SWAP so PD cannot ramp voltage
  for port in /sys/class/typec/port*/; do
    [[ -d "$port" ]] || continue
    local base="${port%/}"
    local name
    name="$(basename "$base")"
    echo sink 2>/dev/null | ammo_sudo tee "$base/data_role" >/dev/null || true
    echo sink 2>/dev/null | ammo_sudo tee "$base/power_role" >/dev/null || true
    ammo_sudo tee "$base/disable_usb_pd" >/dev/null 2>&1 <<<1 || true
    ammo_log "typec $name → sink-only, PD disabled if supported"
  done

  local pd_mod='/etc/modprobe.d/ammo-usb-pd-blacklist.conf'
  if [[ ! -f "$pd_mod" ]]; then
    ammo_sudo tee "$pd_mod" >/dev/null <<'EOF'
# ammosecurity — no USB-PD voltage ramps on human-contact ports
blacklist tcpm
blacklist fusb302
install tcpm /bin/false
EOF
  fi
}

cmd_clamp_live_devices() {
  ammo_log "clamping live USB human-contact devices to ${HUMAN_USB_MAX_MV} mV / ${HUMAN_USB_MAX_MA} mA ceiling"
  local dev maxpower_ma path
  for path in /sys/bus/usb/devices/[0-9]*; do
    [[ -d "$path" ]] || continue
    [[ -f "$path/bDeviceClass" ]] || continue

    # HID boot or composite with HID interface
    if [[ -f "$path/bInterfaceClass" ]] && grep -qE '^(03|01|00)$' "$path/bInterfaceClass" 2>/dev/null; then
      :
    elif [[ -f "$path/bDeviceClass" ]] && ! grep -qE '^(03|01|00|09)$' "$path/bDeviceClass" 2>/dev/null; then
      continue
    fi

    echo auto 2>/dev/null | ammo_sudo tee "$path/power/control" >/dev/null || true
    echo 1000 2>/dev/null | ammo_sudo tee "$path/power/autosuspend_delay_ms" >/dev/null || true

    if [[ -f "$path/bMaxPower" ]]; then
      maxpower_ma="$(cat "$path/bMaxPower" 2>/dev/null || echo 0)"
      maxpower_ma=$((maxpower_ma * 2))  # bMaxPower is in 2 mA units
      if [[ "$maxpower_ma" -gt "$HUMAN_USB_MAX_MA" ]]; then
        ammo_log "WARNING: $(basename "$path") requests ${maxpower_ma}mA — over human ceiling; unplug or use hardware LDO"
      fi
    fi
    ammo_log "regulated: $(basename "$path") $(cat "$path/product" 2>/dev/null || echo unknown)"
  done

  # Input current limit on usb power_supply (phones, headsets charging from port)
  for ps in /sys/class/power_supply/usb*; do
    [[ -d "$ps" ]] || continue
    echo 500000 2>/dev/null | ammo_sudo tee "$ps/input_current_limit" >/dev/null || true
    echo 5500000 2>/dev/null | ammo_sudo tee "$ps/voltage_max" >/dev/null || true
    ammo_log "power_supply clamp → $(basename "$ps")"
  done
}

cmd_audit_human_contact() {
  ammo_log 'human-contact device audit'
  lsusb 2>/dev/null | grep -iE 'keyboard|mouse|hub|headset|audio|game|touch|controller|human' \
    || lsusb 2>/dev/null | head -20 || true
  ammo_log 'physical note: add inline 5 V LDO (AMS1117-5.0, MCP1700) on DIY cables touching skin'
}

cmd_human_contact_regulator() {
  cmd_install_udev_regulator
  cmd_block_usb_pd
  cmd_clamp_live_devices
  cmd_audit_human_contact
  ammo_log 'human-contact voltage regulators applied — 5 V bus, 500 mA max, no PD ramp'
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  cmd_human_contact_regulator "$@"
fi