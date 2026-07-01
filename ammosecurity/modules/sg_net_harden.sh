#!/usr/bin/env bash
# net_harden — deny inbound, kill SMB, IPv6 off, kernel sysctl hardening
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/common.sh"

cmd_kernel_harden() {
  ammo_log 'kernel sysctl hardening'
  ammo_sudo sysctl -w kernel.kptr_restrict=2
  ammo_sudo sysctl -w kernel.dmesg_restrict=1
  ammo_sudo sysctl -w kernel.perf_event_paranoid=3
  ammo_sudo sysctl -w vm.mmap_min_addr=65536
  ammo_sudo sysctl -w kernel.unprivileged_bpf_disabled=1
  ammo_sudo sysctl -w kernel.yama.ptrace_scope=3
  ammo_sudo sysctl -w net.core.bpf_jit_harden=2
}

cmd_no_samba() {
  ammo_log 'kill Samba / SMB (139/445)'
  for unit in smbd nmbd smb winbind; do
    ammo_service_off "$unit"
  done
  if ss -tlnp 2>/dev/null | grep -qE ':139|:445'; then
    ammo_log 'WARNING: still listening on 139/445'
    ss -tlnp | grep -E ':139|:445' || true
  else
    ammo_log 'OK: 139/445 closed'
  fi
}

cmd_firewall() {
  ammo_log 'firewall: sg_build owns policy — iptables only, no ufw'
  sg_sudo systemctl stop ufw 2>/dev/null || true
  sg_sudo systemctl mask ufw 2>/dev/null || true
  if command -v iptables >/dev/null 2>&1; then
    ammo_sudo iptables -P INPUT DROP
    ammo_sudo iptables -P FORWARD DROP
    ammo_sudo iptables -P OUTPUT ACCEPT
    ammo_sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
    ammo_sudo iptables -A INPUT -i lo -j ACCEPT
  fi
}

cmd_net_harden() {
  cmd_kernel_harden
  cmd_no_samba
  cmd_firewall
  ammo_log 'network hardening complete'
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  cmd_net_harden "$@"
fi