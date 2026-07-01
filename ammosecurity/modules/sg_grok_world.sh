#!/usr/bin/env bash
# grok_world.sh — Grok Build & the World: 30 desktop cleanups via phi · thermo · flow · field
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/common.sh"

run() { local n="$1"; shift; ammo_log "[$n] $*"; "$@" 2>/dev/null || true; }

# ── PHI — wave potential / signal hygiene (1–8) ─────────────────────────
w01_phi_notifications() {
  ammo_log '01 phi: damp notification wave — flat signal, no desktop ripple'
  for svc in notify-osd dunst mako notification-daemon; do ammo_service_off "$svc"; done
  gsettings set org.gnome.desktop.notifications show-banners false 2>/dev/null || true
  gsettings set org.gnome.desktop.notifications show-in-lock-screen false 2>/dev/null || true
}

w02_phi_compositor_calm() {
  ammo_log '02 phi: calm compositor — reduce visual wave churn'
  gsettings set org.gnome.desktop.interface enable-animations false 2>/dev/null || true
  gsettings set org.gnome.mutter experimental-features '[]' 2>/dev/null || true
  kwriteconfig5 --file kwinrc --group Compositing --key Enabled false 2>/dev/null || true
}

w03_phi_dpms_blank() {
  ammo_log '03 phi: DPMS dead band — screen blank kills idle glow encoding'
  command -v xset >/dev/null && xset dpms 300 600 900 2>/dev/null && xset s blank 2>/dev/null || true
}

w04_phi_mouse_smooth() {
  ammo_log '04 phi: smooth input — no acceleration spikes (field probe stable)'
  command -v xinput >/dev/null && xinput list --short 2>/dev/null | grep -i pointer | while read -r _ id _; do
    xinput set-prop "$id" 'libinput Accel Profile Enabled' 0, 1 2>/dev/null || true
  done
}

w05_phi_audio_hush() {
  ammo_log '05 phi: audio hush — idle sink suspend'
  pactl list short sinks 2>/dev/null | awk '{print $1}' | while read -r s; do
    pactl suspend-sink "$s" 0 2>/dev/null || true
  done
  ammo_service_off pipewire-media-session 2>/dev/null || true
}

w06_phi_browser_chatter() {
  ammo_log '06 phi: kill idle browser background waves'
  pkill -f 'chrome.*--type=renderer' 2>/dev/null || true
  systemctl --user mask chromium-browser 2>/dev/null || true
}

w07_phi_wallpaper_flat() {
  ammo_log '07 phi: flat wallpaper — no animated weave on desktop'
  gsettings set org.gnome.desktop.background picture-uri 'file:///usr/share/backgrounds/ubuntu-default-greyscale-wallpaper.png' 2>/dev/null || true
  gsettings set org.mate.background picture-filename '' 2>/dev/null || true
}

w08_phi_tray_flat() {
  ammo_log '08 phi: flatten system tray entropy sources'
  gsettings set org.gnome.shell disable-user-extensions true 2>/dev/null || true
  pkill -x conky 2>/dev/null || true
}

# ── THERMO — heat · entropy · maintenance cost (9–16) ───────────────────
w09_thermo_cpufreq_cool() {
  ammo_log '09 thermo: CPU cool floor — powersave governor'
  for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    [[ -f "$gov" ]] && echo powersave | ammo_sudo tee "$gov" >/dev/null || true
  done
}

w10_thermo_swap_off() {
  ammo_log '10 thermo: swap heat sink off — RAM-only sensitive path'
  ammo_sudo swapoff -a 2>/dev/null || true
}

w11_thermo_journal_vacuum() {
  ammo_log '11 thermo: vacuum journal entropy'
  ammo_sudo journalctl --vacuum-time=3d 2>/dev/null || true
  ammo_sudo journalctl --vacuum-size=200M 2>/dev/null || true
}

w12_thermo_log_scrub() {
  ammo_log '12 thermo: scrub hot log files'
  find "${HOME}/.cache" -name '*.log' -mtime +7 -delete 2>/dev/null || true
  find /tmp -user "$(id -un)" -mtime +1 -delete 2>/dev/null || true
}

w13_thermo_apt_cache() {
  ammo_log '13 thermo: cool apt cache heat'
  ammo_sudo apt-get clean 2>/dev/null || true
  ammo_sudo apt-get autoclean 2>/dev/null || true
}

w14_thermo_thumbnail_purge() {
  ammo_log '14 thermo: purge thumbnail furnace'
  rm -rf "${HOME}/.cache/thumbnails"/* 2>/dev/null || true
  rm -rf "${HOME}/.thumbnails"/* 2>/dev/null || true
}

w15_thermo_zram_tune() {
  ammo_log '15 thermo: zram entropy floor if present'
  [[ -f /sys/block/zram0/disksize ]] && echo 512M | ammo_sudo tee /sys/block/zram0/disksize >/dev/null || true
}

w16_thermo_battery_cap() {
  ammo_log '16 thermo: battery charge cap — reduce heat at 80%'
  for cap in /sys/class/power_supply/BAT*/charge_control_end_threshold; do
    [[ -f "$cap" ]] && echo 80 | ammo_sudo tee "$cap" >/dev/null || true
  done
}

# ── FLOW — velocity · gradients · sync rivers (17–23) ───────────────────
w17_flow_sync_stop() {
  ammo_log '17 flow: stop cloud sync rivers'
  for svc in dropbox onedrive rclone-gdrive syncthing Nextcloud; do ammo_service_off "$svc"; done
  systemctl --user stop 'sync*' 2>/dev/null || true
}

w18_flow_torrent_kill() {
  ammo_log '18 flow: kill peer flood gradients'
  pkill -x transmission-gtk qbittorrent deluge-gtk 2>/dev/null || true
  ammo_service_off transmission-daemon qbittorrent-nox 2>/dev/null || true
}

w19_flow_dns_clean() {
  ammo_log '19 flow: clean DNS channel'
  ammo_sudo systemd-resolve --flush-caches 2>/dev/null || true
  ammo_sudo resolvectl flush-caches 2>/dev/null || true
}

w20_flow_ntp_single() {
  ammo_log '20 flow: single NTP source — no time gradient chaos'
  ammo_sudo timedatectl set-ntp true 2>/dev/null || true
}

w21_flow_ipv6_off() {
  ammo_log '21 flow: IPv6 gradient off'
  ammo_sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1 2>/dev/null || true
  ammo_sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1 2>/dev/null || true
}

w22_flow_mail_idle() {
  ammo_log '22 flow: idle mail sync off'
  ammo_service_off postfix dovecot 2>/dev/null || true
  systemctl --user stop evolution-calendar evolution-addressbook 2>/dev/null || true
}

w23_flow_cups_quiet() {
  ammo_log '23 flow: quiet print discovery flow'
  ammo_service_off cups cups-browsed 2>/dev/null || true
}

# ── FIELD — desktop substrate / die clean (24–30) ───────────────────────
w24_field_autostart_scrub() {
  ammo_log '24 field: scrub autostart bloat'
  local d="${HOME}/.config/autostart"
  [[ -d "$d" ]] && find "$d" -name '*.desktop' -print -delete 2>/dev/null || true
}

w25_field_snap_trim() {
  ammo_log '25 field: trim snap substrate'
  command -v snap >/dev/null && ammo_sudo snap set system refresh.hold="$(date -d '+30 days' +%Y-%m-%dT%H:%M:%S%z 2>/dev/null || date +%Y-%m-%d)" 2>/dev/null || true
}

w26_field_telemetry_zero() {
  ammo_log '26 field: telemetry slots zeroed'
  for svc in apport whoopsie snapd snapd.socket ubuntu-report motd-news; do ammo_service_off "$svc"; done
  ammo_sudo chmod -x /etc/update-motd.d/* 2>/dev/null || true
}

w27_field_cron_audit() {
  ammo_log '27 field: cron bus audit'
  crontab -l 2>/dev/null || ammo_log 'no user crontab'
  ammo_sudo ls -la /etc/cron.* 2>/dev/null | head -20 || true
}

w28_field_duplicate_fm() {
  ammo_log '28 field: single file manager focus'
  pkill -x nautilus dolphin thunar nemo 2>/dev/null || true
}

w29_field_ssh_harden() {
  ammo_log '29 field: ssh ingress hardened'
  local f=/etc/ssh/sshd_config.d/ammo-world.conf
  ammo_sudo tee "$f" >/dev/null <<'EOF'
PasswordAuthentication no
PermitRootLogin no
X11Forwarding no
AllowTcpForwarding no
EOF
  ammo_sudo systemctl reload sshd 2>/dev/null || ammo_sudo systemctl reload ssh 2>/dev/null || true
}

w30_field_world_status() {
  ammo_log '30 field: Grok Build world status — phi/thermo/flow snapshot'
  echo '--- phi ---'; pgrep -a dunst mako conky 2>/dev/null || echo 'flat'
  echo '--- thermo ---'; ammo_sudo sensors 2>/dev/null | head -8 || cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null || true
  echo '--- flow ---'; ss -tunp 2>/dev/null | head -10 || true
  echo '--- field ---'; df -h / /home 2>/dev/null | head -4 || true
  ammo_log 'Grok Build & the World — desktop computing cleaned'
}

ALL_WORLD=(
  w01_phi_notifications w02_phi_compositor_calm w03_phi_dpms_blank
  w04_phi_mouse_smooth w05_phi_audio_hush w06_phi_browser_chatter
  w07_phi_wallpaper_flat w08_phi_tray_flat
  w09_thermo_cpufreq_cool w10_thermo_swap_off w11_thermo_journal_vacuum
  w12_thermo_log_scrub w13_thermo_apt_cache w14_thermo_thumbnail_purge
  w15_thermo_zram_tune w16_thermo_battery_cap
  w17_flow_sync_stop w18_flow_torrent_kill w19_flow_dns_clean
  w20_flow_ntp_single w21_flow_ipv6_off w22_flow_mail_idle w23_flow_cups_quiet
  w24_field_autostart_scrub w25_field_snap_trim w26_field_telemetry_zero
  w27_field_cron_audit w28_field_duplicate_fm w29_field_ssh_harden
  w30_field_world_status
)

cmd_grok_world() {
  local which="${1:-all}"
  ammo_log '=== GROK BUILD & THE WORLD — phi · thermo · flow · field ==='
  if [[ "$which" == 'all' || "$which" == 'All' ]]; then
    for fn in "${ALL_WORLD[@]}"; do "$fn"; done
  elif [[ "$which" =~ ^[0-9]+$ ]]; then
    local idx="w$(printf '%02d' "$which")"
    for fn in "${ALL_WORLD[@]}"; do
      [[ "$fn" == ${idx}* ]] && "$fn" && return 0
    done
    ammo_log "no world update #$which"
  else
    for fn in "${ALL_WORLD[@]}"; do
      [[ "$fn" == *"$which"* ]] && "$fn"
    done
  fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  cmd_grok_world "${1:-all}"
fi