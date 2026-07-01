#!/usr/bin/env bash
# sg_firmware — internet + no bullshit. No security tools. No hacking tools. We are the layer.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/common.sh"

PURGE_SECURITY=(
  clamav clamav-daemon clamav-freshclam
  rkhunter chkrootkit aide aide-common tiger lynis
  fail2ban ufw gufw snort suricata crowdsec
  maldet sophosav eset nod32 bitdefender
  apparmor-profiles unattended-upgrades
)

PURGE_HACKING=(
  nmap masscan zmap
  metasploit-framework
  aircrack-ng reaver bully mdk3 mdk4
  hashcat john hydra
  sqlmap nikto dirb gobuster ffuf
  wireshark tshark tcpdump
  burpsuite ettercap-text-only dsniff
  netcat-traditional ncat netcat-openbsd
  proxychains4 proxychains-ng
  legion impacket-scripts responder bettercap
  python3-scapy scapy
  bloodhound crackmapexec
  ncrack medusa
)

KILL_PROCS=(
  nmap masscan msfconsole msfvenom
  aircrack-ng aireplay-ng airodump-ng
  hashcat john hydra sqlmap
  wireshark tshark tcpdump
  burpsuite ettercap bettercap responder
  nc ncat netcat
  clamscan freshclam fail2ban-server
)

cmd_purge_packages() {
  sg_log 'drop security + hacking packages'
  command -v dpkg >/dev/null 2>&1 || return 0
  local pkg
  for pkg in "${PURGE_SECURITY[@]}" "${PURGE_HACKING[@]}"; do
    dpkg -l "$pkg" &>/dev/null || continue
    sg_sudo apt-get remove --purge -y "$pkg" 2>/dev/null && sg_log "gone: $pkg" || true
  done
  sg_sudo apt-get autoremove -y 2>/dev/null || true
}

cmd_kill_tool_processes() {
  sg_log 'kill security + hacking processes'
  local name
  for name in "${KILL_PROCS[@]}"; do
    pkill -x "$name" 2>/dev/null || true
    pkill -f "$name" 2>/dev/null || true
  done
}

cmd_mask_bullshit_services() {
  sg_log 'mask bullshit daemons'
  local svc
  for svc in clamav-freshclam clamav-daemon fail2ban ufw snort suricata \
    tor openvpn@client; do
    sg_service_off "$svc"
  done
}

cmd_internet_only() {
  sg_log 'internet out only — no inbound bullshit'
  sg_sudo systemctl stop ufw fail2ban 2>/dev/null || true
  sg_sudo systemctl mask ufw fail2ban 2>/dev/null || true
  if command -v iptables >/dev/null 2>&1; then
    sg_sudo iptables -P INPUT DROP 2>/dev/null || true
    sg_sudo iptables -P FORWARD DROP 2>/dev/null || true
    sg_sudo iptables -P OUTPUT ACCEPT 2>/dev/null || true
    sg_sudo iptables -C INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || \
      sg_sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || true
    sg_sudo iptables -C INPUT -i lo -j ACCEPT 2>/dev/null || \
      sg_sudo iptables -A INPUT -i lo -j ACCEPT 2>/dev/null || true
  fi
}

cmd_sg_firmware() {
  sg_log '=== SG FIRMWARE — internet + no bullshit ==='
  cmd_purge_packages
  cmd_kill_tool_processes
  cmd_mask_bullshit_services
  cmd_internet_only
  sg_sudo mkdir -p /var/lib/sg_build 2>/dev/null || true
  date -Is 2>/dev/null | sg_sudo tee /var/lib/sg_build/firmware-layer >/dev/null || true
  sg_log 'done — no security tools, no hacking tools, just internet'
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  cmd_sg_firmware "$@"
fi