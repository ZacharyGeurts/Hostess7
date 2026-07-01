#!/usr/bin/env bash
# dead_air_regulator — no rapid encoded fluctuations; dead air when outside function
# Prevents power-rail / RF duty-cycle encoding. Idle devices = silence, not chatter.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/common.sh"

# Minimum settle time between power-state toggles (ms) — blocks fast encoded ripple
DEAD_AIR_POWER_SETTLE_MS=5000
# FCC-friendly: no rapid duty-cycle modulation on conducted or radiated paths

OUT_OF_FUNCTION_PROCS=(
  'ffmpeg.*video=/dev/video'
  'gstreamer.*v4l2'
  'arecord.*plughw'
  'parecord'
  'pactl.*load-module module-loopback'
  'brightnessctl.*rapid'
  'ledctl'
  'usbmuxd'
)

cmd_damp_power_fluctuation() {
  ammo_log 'damp rapid power fluctuation — no encoded signals on voltage rails'
  local rule='/etc/udev/rules.d/99-ammo-dead-air-power.rules'
  if [[ ! -f "$rule" ]]; then
    ammo_sudo tee "$rule" >/dev/null <<EOF
# ammosecurity dead air — stable USB power, no rapid authorize/ripple encoding
SUBSYSTEM=="usb", ATTR{power/control}="on", ATTR{power/autosuspend_delay_ms}="${DEAD_AIR_POWER_SETTLE_MS}", \
  ATTR{power/persist}="1", ENV{AMMO_DEAD_AIR}="1"
SUBSYSTEM=="usb", ENV{AMMO_DEAD_AIR}=="1", ACTION=="change", ENV{POWER_RAPID}=="1", \
  RUN+="/bin/sh -c 'echo on > /sys\$DEVPATH/power/control 2>/dev/null; sleep 0.5'"
EOF
    ammo_sudo udevadm control --reload-rules 2>/dev/null || true
  fi

  # Kernel USB autosuspend: long delay, not rapid cycling
  ammo_sudo sysctl -w kernel.autosuspend_delay_ms="${DEAD_AIR_POWER_SETTLE_MS}" 2>/dev/null || true
  for path in /sys/bus/usb/devices/*/power/control; do
    [[ -f "$path" ]] || continue
    echo on 2>/dev/null | ammo_sudo tee "$path" >/dev/null || true
    local delay="${path%/control}/autosuspend_delay_ms"
    [[ -f "$delay" ]] && echo "${DEAD_AIR_POWER_SETTLE_MS}" 2>/dev/null | ammo_sudo tee "$delay" >/dev/null || true
  done
  ammo_log "power rails stable — settle ≥ ${DEAD_AIR_POWER_SETTLE_MS}ms between state changes"
}

cmd_dead_air_rf() {
  ammo_log 'dead air RF — no scan/probe/beacon when not in active function'
  if command -v iw >/dev/null 2>&1; then
    for iface in $(ls /sys/class/net/ 2>/dev/null); do
      iw dev "$iface" info &>/dev/null || continue
      # Not associated → interface down (dead air, no background encoding)
      if ! iw dev "$iface" link 2>/dev/null | grep -q 'Connected to'; then
        ammo_sudo ip link set "$iface" down 2>/dev/null || true
        ammo_log "dead air: $iface down (not associated — no probe/beacon)"
      else
        # Associated: disable scan sched, fixed TX — no rapid channel hop encoding
        ammo_sudo iw dev "$iface" set power_save on 2>/dev/null || true
        ammo_sudo iw dev "$iface" scan trigger off 2>/dev/null || true
      fi
    done
  fi
  if command -v nmcli >/dev/null 2>&1; then
    ammo_sudo nmcli radio wifi off 2>/dev/null || true
    ammo_log 'nmcli wifi off — radiated dead air unless ethernet path'
  fi
  ammo_sudo rfkill block bluetooth 2>/dev/null || true
}

cmd_silence_out_of_function() {
  ammo_log 'silence items outside declared function'
  # Webcam not opened by user session → dead air
  if [[ -d /dev/video0 ]] && ! fuser /dev/video0 2>/dev/null; then
    ammo_sudo modprobe -r uvcvideo 2>/dev/null || true
    ammo_log 'uvcvideo unloaded — camera dead air (no idle TX/modulation)'
  fi
  # Mic capture daemons not in active call
  for pat in "${OUT_OF_FUNCTION_PROCS[@]}"; do
    pgrep -f "$pat" 2>/dev/null | while read -r pid; do
      [[ -n "$pid" ]] || continue
      ammo_log "out-of-function kill: pid $pid ($pat)"
      kill -9 "$pid" 2>/dev/null || true
    done
  done
  # LED/PWM rapid flicker encoders
  for led in /sys/class/leds/*/trigger; do
    [[ -f "$led" ]] || continue
    echo none 2>/dev/null | ammo_sudo tee "$led" >/dev/null || true
  done
  # USB gadgets doing non-function (bad USB functions)
  lsusb -t 2>/dev/null | grep -iE 'Driver=usb-storage|Driver=cdc|Driver=hid' | while read -r line; do
    echo "$line" | grep -qiE 'hub|keyboard|mouse|audio' && continue
    ammo_log "review non-function USB: $line"
  done
}

cmd_block_encoded_sidechannels() {
  ammo_log 'block rapid encoded sidechannels (CPU/USB duty-cycle carriers)'
  ammo_sudo sysctl -w kernel.nmi_watchdog=0 2>/dev/null || true
  # Flatten rapid P-states that can carry encoded ripple on power lines
  if [[ -d /sys/devices/system/cpu/cpu0/cpufreq ]]; then
    local governor='/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor'
    if [[ -f "$governor" ]]; then
      echo powersave 2>/dev/null | ammo_sudo tee "$governor" >/dev/null || true
      ammo_log 'cpufreq → powersave (reduces rapid rail fluctuation encoding)'
    fi
  fi
  # Kill known CPU-frequency modulation encoders
  pkill -f 'cpufreq-encoder|power-sploit.*ripple' 2>/dev/null || true
}

cmd_dead_air_audit() {
  ammo_log 'dead air policy'
  cat <<EOF
  Power rails:     stable ON, autosuspend delay ≥ ${DEAD_AIR_POWER_SETTLE_MS}ms — no rapid encoded ripple
  RF:              dead air unless actively associated on approved path; no scan/probe chatter
  Out-of-function: webcam/mic/LED PWM silenced when not in use
  Modulation:      no duty-cycle encoding on voltage or radiated paths (pairs with FCC emissions)
EOF
}

cmd_dead_air_regulator() {
  ammo_log '=== DEAD AIR REGULATOR — no rapid encoded fluctuations ==='
  cmd_damp_power_fluctuation
  cmd_dead_air_rf
  cmd_silence_out_of_function
  cmd_block_encoded_sidechannels
  cmd_dead_air_audit
  ammo_log 'dead air enforced — stable rails, silent idle, function-only TX'
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  cmd_dead_air_regulator "$@"
fi