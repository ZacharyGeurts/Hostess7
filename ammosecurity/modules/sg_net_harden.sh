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

cmd_ipv6_off() {
  ammo_log 'IPv6 — disable on all interfaces (stealth egress guard)'
  ammo_sudo sysctl -w net.ipv6.conf.all.disable_ipv6=1
  ammo_sudo sysctl -w net.ipv6.conf.default.disable_ipv6=1
  ammo_sudo sysctl -w net.ipv6.conf.lo.disable_ipv6=0
}

cmd_no_samba() {
  ammo_log 'kill Samba / SMB (139/445)'
  for unit in smbd nmbd smb winbind; do
    ammo_service_off "$unit"
  done
  if ss -tlnp 2>/dev/null | grep -qE ':139|:445'; then
    ammo_violation 'Samba still listening on 139/445'
    ss -tlnp | grep -E ':139|:445' || true
  else
    ammo_log 'OK: 139/445 closed'
  fi
}

cmd_firewall() {
  ammo_log 'firewall: sg_build owns policy — iptables + nft guard'
  ammo_sudo systemctl stop ufw 2>/dev/null || true
  ammo_sudo systemctl mask ufw 2>/dev/null || true
  if command -v iptables >/dev/null 2>&1; then
    ammo_sudo iptables -P INPUT DROP
    ammo_sudo iptables -P FORWARD DROP
    ammo_sudo iptables -P OUTPUT ACCEPT
    ammo_sudo iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
    ammo_sudo iptables -A INPUT -i lo -j ACCEPT
  fi
  bash "$(dirname "${BASH_SOURCE[0]}")/interface_guard.sh" apply 2>/dev/null || true
}

cmd_status() {
  ammo_ensure_state
  ammo_log '=== Bot Net / Net Health Status ==='
  echo "ptrace_scope: $(sysctl -n kernel.yama.ptrace_scope 2>/dev/null || echo '?')"
  echo "ipv6_all: $(sysctl -n net.ipv6.conf.all.disable_ipv6 2>/dev/null || echo '?')"
  echo "samba_ports: $(ss -tlnp 2>/dev/null | grep -E ':139|:445' || echo 'None — OK')"
  echo "iptables_INPUT: $(iptables -S INPUT 2>/dev/null | head -1 || echo '?')"
  echo "ufw: $(systemctl is-enabled ufw 2>/dev/null || echo 'masked/stopped')"
  if command -v nft >/dev/null 2>&1; then
    nft list table inet ammo_guard 2>/dev/null | head -5 || echo 'nft ammo_guard: not loaded'
  fi
  ammo_health_note 'net_harden status check'
  ammo_log "violations: ${AMMO_VIOLATIONS_LOG}"
}

cmd_drift_check() {
  local drift=0
  local ptrace
  ptrace="$(sysctl -n kernel.yama.ptrace_scope 2>/dev/null || echo 0)"
  [[ "$ptrace" -ge 2 ]] || { ammo_violation "ptrace_scope drift ($ptrace)"; drift=1; }
  if ss -tlnp 2>/dev/null | grep -qE ':139|:445'; then
    ammo_violation 'Samba ports open'
    drift=1
  fi
  if systemctl is-active ufw &>/dev/null; then
    ammo_violation 'ufw active — should be masked'
    drift=1
  fi
  return "$drift"
}

cmd_dry_run() {
  ammo_log 'DRY-RUN net_harden — reporting only'
  cmd_status
}

cmd_net_harden() {
  local mode="${1:-apply}"
  case "$mode" in
    status) cmd_status; return 0 ;;
    dry-run|test) cmd_dry_run; return 0 ;;
    drift) cmd_drift_check; return $? ;;
    killswitch|airgap)
      bash "$(dirname "${BASH_SOURCE[0]}")/interface_guard.sh" killswitch
      return 0
      ;;
  esac
  cmd_kernel_harden
  cmd_ipv6_off
  cmd_no_samba
  cmd_firewall
  ammo_health_note 'net_harden applied'
  ammo_log 'network hardening complete'
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  cmd_net_harden "${1:-apply}"
fi