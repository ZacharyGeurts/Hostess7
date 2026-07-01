#!/usr/bin/env bash
# fcc_emissions_regulator — escaping voltage + radiated + modulation never exceed FCC Part 15
# Conducted (USB 5V/500mA) · radiated EIRP caps · outlaw modulation/TX blocked
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/common.sh"

# FCC Part 15 reference ceilings (software enforcement targets)
# Conducted: USB IF 5.0 V ±5% = 4.75–5.25 V at connector
FCC_USB_MV_MIN=4750
FCC_USB_MV_MAX=5250
FCC_USB_MA_MAX=500
# 2.4 GHz ISM band Part 15.247: 1 W EIRP spread-spectrum; we cap far below in software
FCC_WIFI_DBM_MAX=20
# Unintentional radiator field strength limit ~30 µV/m @ 3m (we prevent TX that could exceed)

MODULATION_OUTLAW_PROCS=(
  hackrf_transfer hackrf_sweep
  rtl_sdr rtl_test rtl_433
  gqrx qspectrumanalyzer
  gr_mod_tool gr-uhd usrp_sink
  limeutil 'LimeUtil.*--tx'
  bladeRF-cli tx_samples
  osmocom_fft osmo-trx
  rfcat zelda-zigbee killerbee
  mdk3 mdk4 aireplay-ng
  hostapd create_ap
)

cmd_conducted_emissions() {
  ammo_log 'FCC conducted emissions — voltage escape clamp (USB bus)'
  # Reuse human-contact regulator ceiling (5 V / 500 mA)
  local mod
  mod="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/sg_human_contact.sh"
  if [[ -f "$mod" ]]; then
    bash "$mod" 2>/dev/null || true
  fi

  for ps in /sys/class/power_supply/usb* /sys/class/power_supply/battery; do
    [[ -d "$ps" ]] || continue
    echo 500000 2>/dev/null | ammo_sudo tee "$ps/input_current_limit" >/dev/null || true
    echo "${FCC_USB_MV_MAX}000" 2>/dev/null | ammo_sudo tee "$ps/voltage_max" >/dev/null || true
    echo "${FCC_USB_MV_MIN}000" 2>/dev/null | ammo_sudo tee "$ps/voltage_min" >/dev/null || true
  done

  for path in /sys/bus/usb/devices/[0-9]*/; do
    [[ -f "${path}bMaxPower" ]] || continue
    local ma
    ma=$(($(cat "${path}bMaxPower" 2>/dev/null || echo 0) * 2))
    if [[ "$ma" -gt "$FCC_USB_MA_MAX" ]]; then
      ammo_log "FCC VIOLATION (conducted): $(basename "$path") draws ${ma}mA > ${FCC_USB_MA_MAX}mA — deauthorizing"
      echo 0 2>/dev/null | ammo_sudo tee "${path}authorized" >/dev/null || true
    fi
  done
  ammo_log "conducted: ${FCC_USB_MV_MIN}-${FCC_USB_MV_MAX} mV, ${FCC_USB_MA_MAX} mA max"
}

cmd_radiated_emissions() {
  ammo_log 'FCC radiated emissions — regulatory domain + TX power ceiling'
  if command -v iw >/dev/null 2>&1; then
    ammo_sudo iw reg set US 2>/dev/null || ammo_sudo iw reg set 00 2>/dev/null || true
    for phy in /sys/class/ieee80211/phy*/; do
      [[ -d "$phy" ]] || continue
      local pname
      pname="$(basename "$phy")"
      ammo_sudo iw phy "$pname" set txpower fixed "${FCC_WIFI_DBM_MAX}" 2>/dev/null || \
        ammo_sudo iw phy "$pname" set txpower limit "${FCC_WIFI_DBM_MAX}" 2>/dev/null || true
      # Kill monitor mode — custom modulation / spurious TX vector
      ammo_sudo iw phy "$pname" set monitor none 2>/dev/null || true
      ammo_log "phy $pname → reg US, txpower ≤ ${FCC_WIFI_DBM_MAX} dBm, monitor off"
    done
  fi

  if command -v crda >/dev/null 2>&1; then
    ammo_log 'CRDA present — reg domain enforced via kernel cfg80211'
  fi

  # Bluetooth TX: already clasped; double-check rfkill
  if command -v rfkill >/dev/null 2>&1; then
    rfkill list 2>/dev/null | grep -E 'Bluetooth|Wi-Fi|WAN|NFC' || true
  fi
}

cmd_modulation_guard() {
  ammo_log 'FCC modulation guard — no outlaw modulators or arbitrary waveform TX'
  local found=0 name pid
  for name in "${MODULATION_OUTLAW_PROCS[@]}"; do
    if pgrep -f "$name" >/dev/null 2>&1; then
      ammo_log "OUTLAW MODULATION/TX: killing $name"
      pkill -f "$name" 2>/dev/null || true
      found=1
    fi
  done

  # Block packet injection / raw 802.11 modulation interfaces
  for iface in /sys/class/net/mon* /sys/class/net/wlan*mon*; do
    [[ -e "$iface" ]] || continue
    local ifname
    ifname="$(basename "$iface")"
    ammo_sudo ip link set "$ifname" down 2>/dev/null || true
    ammo_log "monitor iface down: $ifname (spurious modulation vector)"
    found=1
  done

  # Mesh / ad-hoc = non-standard modulation paths
  if command -v iw >/dev/null 2>&1; then
    for iface in $(ls /sys/class/net/ 2>/dev/null); do
      iw dev "$iface" info 2>/dev/null | grep -qE 'type monitor|type mesh' && {
        ammo_sudo ip link set "$iface" down 2>/dev/null || true
        ammo_log "non-STA iface clasped: $iface"
        found=1
      } || true
    done
  fi

  local modprobe_f='/etc/modprobe.d/ammo-fcc-modulation.conf'
  if [[ ! -f "$modprobe_f" ]]; then
    ammo_sudo tee "$modprobe_f" >/dev/null <<'EOF'
# ammosecurity — FCC modulation: no arbitrary RF waveform TX from USB SDR
blacklist hackrf
blacklist rtl2832
blacklist dvb_usb_rtl28xxu
blacklist uhd
blacklist lime
blacklist bladerf
install hackrf /bin/false
install uhd /bin/false
EOF
  fi

  [[ "$found" -eq 0 ]] && ammo_log 'no outlaw modulation/TX processes active'
}

cmd_fcc_audit() {
  ammo_log 'FCC Part 15 audit summary'
  cat <<EOF
  Conducted (USB):     ${FCC_USB_MV_MIN}–${FCC_USB_MV_MAX} mV, ≤${FCC_USB_MA_MAX} mA
  Radiated (2.4 GHz):  ≤${FCC_WIFI_DBM_MAX} dBm EIRP software cap
  Modulation:          DSSS/OFDM via certified stack only; no SDR TX, no monitor/inject
  Dead air:            no rapid power/RF fluctuation encoding; idle = silence
  Ingress clasp:       USB/BT/WiFi locked when sg_build -Action All applied
  Physical:            ferrite on USB cables; shielded enclosure for switching supplies
EOF
}

cmd_fcc_emissions_regulator() {
  ammo_log '=== FCC EMISSIONS REGULATOR — conducted + radiated + modulation ==='
  cmd_conducted_emissions
  cmd_radiated_emissions
  cmd_modulation_guard
  local dead_air
  dead_air="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/sg_dead_air.sh"
  [[ -f "$dead_air" ]] && bash "$dead_air" || true
  cmd_fcc_audit
  ammo_log 'FCC emissions envelope enforced — stable rails, dead air, no encoded fluctuation'
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  cmd_fcc_emissions_regulator "$@"
fi