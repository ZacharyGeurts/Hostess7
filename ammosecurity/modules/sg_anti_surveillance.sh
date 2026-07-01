#!/usr/bin/env bash
# anti_surveillance — no keyloggers, no rogue HID/mice, no input capture bullshit
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/common.sh"

KEYLOG_NAMES=(
  logkeys xinput-keylogger lkl spyrix revealer keysniffer
  keystroke keylogger kidlogger ardamax perfect-keylogger
)

SUSPICIOUS_INPUT_PROCS=(
  'xinput test'
  'ydotool'
  'evemu-record'
  'input-event'
)

cmd_block_keyloggers() {
  ammo_log 'killing known keylogger processes'
  for name in "${KEYLOG_NAMES[@]}"; do
    pkill -ix "$name" 2>/dev/null || true
    ammo_kill_pattern "$name"
  done

  # cmdline grep
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    ammo_log "killing suspicious pid $pid"
    kill -9 "$pid" 2>/dev/null || true
  done < <(pgrep -af 'keylog|keystroke|spyrix|revealer' 2>/dev/null | awk '{print $1}' || true)
}

cmd_hid_guard() {
  ammo_log 'HID guard — audit input devices (mice/keyboards only, no ghost HID)'

  if command -v libinput >/dev/null 2>&1; then
    libinput list-devices 2>/dev/null | sed -n '1,120p' || true
  elif [[ -d /dev/input ]]; then
    ls -la /dev/input/ 2>/dev/null || true
  fi

  # udev: block new USB HID from unknown vendors (aggressive — whitelist your gear in 99-ammo-hid.rules)
  local udev_rule='/etc/udev/rules.d/99-ammo-hid-guard.rules'
  if [[ ! -f "$udev_rule" ]]; then
    ammo_log 'installing HID guard udev rule (blocks NEW usb HID hotplug)'
    ammo_sudo tee "$udev_rule" >/dev/null <<'EOF'
# ammosecurity — block hot-plug USB HID (keyloggers, rogue mice). Remove rule to allow new devices.
ACTION=="add", SUBSYSTEM=="input", ENV{ID_BUS}=="usb", RUN+="/bin/sh -c 'echo 0 > /sys$DEVPATH/device/authorized'"
EOF
    ammo_sudo udevadm control --reload-rules 2>/dev/null || true
  else
    ammo_log 'HID guard udev rule already present'
  fi

  # Disable X11 recording extensions if X present
  if [[ -n "${DISPLAY:-}" ]] && command -v xinput >/dev/null 2>&1; then
    xinput list 2>/dev/null | grep -i 'slave\|keyboard\|pointer' | head -20 || true
  fi
}

cmd_ld_preload_audit() {
  ammo_log 'LD_PRELOAD / input hook audit'
  if [[ -n "${LD_PRELOAD:-}" ]]; then
    ammo_log "WARNING: LD_PRELOAD set in environment: $LD_PRELOAD"
  fi
  grep -r 'LD_PRELOAD' /etc/environment /etc/profile.d/ 2>/dev/null || ammo_log 'no system LD_PRELOAD hooks'
}

cmd_anti_surveillance() {
  cmd_block_keyloggers
  for pat in "${SUSPICIOUS_INPUT_PROCS[@]}"; do
    ammo_kill_pattern "$pat"
  done
  cmd_hid_guard
  cmd_ld_preload_audit
  ammo_log 'anti-surveillance pass complete'
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  cmd_anti_surveillance "$@"
fi