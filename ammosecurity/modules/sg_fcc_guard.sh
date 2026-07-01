#!/usr/bin/env bash
# fcc_guard — lock down outlaw RF: BT, rogue AP, SDR transmit, NFC, packet relay
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/common.sh"

SDR_PROCS=(
  hackrf_transfer rtl_433 rtl_sdr gqrx qspectrumanalyzer
  urh limeutil bladeRF gr-osmosdr
)

cmd_rfkill_lock() {
  if ! command -v rfkill >/dev/null 2>&1; then
    ammo_log 'rfkill missing — install: sudo apt install rfkill'
    return 0
  fi
  ammo_log 'rfkill: block bluetooth + nfc (wifi left up for outbound)'
  while read -r idx _; do
    [[ -n "$idx" ]] || continue
    ammo_sudo rfkill block "$idx" 2>/dev/null || true
  done < <(rfkill list bluetooth 2>/dev/null | awk '/^[0-9]+:/{print $1}' | tr -d ':')
  while read -r idx _; do
    [[ -n "$idx" ]] || continue
    ammo_sudo rfkill block "$idx" 2>/dev/null || true
  done < <(rfkill list nfc 2>/dev/null | awk '/^[0-9]+:/{print $1}' | tr -d ':')
}

cmd_block_rogue_ap() {
  ammo_log 'blocking rogue AP / relay services'
  for unit in hostapd create_ap dnsmasq; do
    ammo_service_off "$unit"
  done
  ammo_sudo sysctl -w net.ipv4.ip_forward=0 2>/dev/null || true
  ammo_sudo sysctl -w net.ipv6.conf.all.forwarding=0 2>/dev/null || true
}

cmd_sdr_sweep() {
  ammo_log 'SDR / outlaw transmitter process sweep'
  local found=0
  for name in "${SDR_PROCS[@]}"; do
    if pgrep -x "$name" >/dev/null 2>&1 || pgrep -f "$name" >/dev/null 2>&1; then
      ammo_log "WARNING: SDR/transmit tool running: $name"
      found=1
    fi
  done
  [[ "$found" -eq 0 ]] && ammo_log 'no SDR transmit daemons detected'
}

cmd_modprobe_blacklist() {
  local f='/etc/modprobe.d/ammo-fcc-blacklist.conf'
  if [[ -f "$f" ]]; then
    ammo_log 'FCC modprobe blacklist already installed'
    return 0
  fi
  ammo_log 'blacklisting common SDR USB modules (unload after plug)'
  ammo_sudo tee "$f" >/dev/null <<'EOF'
# ammosecurity FCC guard — block casual SDR USB without explicit admin remove
blacklist hackrf
blacklist rtl2832
blacklist rtl2830
blacklist dvb_usb_rtl28xxu
install hackrf /bin/false
install rtl2832 /bin/false
EOF
}

cmd_fcc_guard() {
  cmd_rfkill_lock
  cmd_block_rogue_ap
  cmd_sdr_sweep
  cmd_modprobe_blacklist
  local emissions
  emissions="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/sg_fcc_emissions.sh"
  [[ -f "$emissions" ]] && bash "$emissions" || true
  ammo_log 'FCC guard pass complete — no outlaw BT/NFC/AP relay + emissions envelope'
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  cmd_fcc_guard "$@"
fi