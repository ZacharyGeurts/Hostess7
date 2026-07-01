# AmmoLang boundary route — AML_BUILD=1 universal boundary
_aml_find_root() {
  local d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  while [[ "$d" != "/" ]]; do
    [[ -f "$d/lib/ammolang-run.sh" ]] && echo "$d" && return 0
    d="$(dirname "$d")"
  done
  return 1
}
if [[ "${AML_BUILD:-1}" != "0" ]] && [[ -z "${AML_BOUNDARY_ACTIVE:-}" ]]; then
  _AML_ROOT="$(_aml_find_root 2>/dev/null || true)"
  if [[ -n "$_AML_ROOT" ]]; then
    export AML_BOUNDARY_ACTIVE=1
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-perimeter-enforce.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS Field Perimeter enforce — sysctl edge + nftables multicast leak block.
set -euo pipefail

nexus_perimeter_sysctl_apply() {
  [[ "${NEXUS_PERIMETER_APPLY:-0}" == "1" ]] || return 0
  local key val
  while IFS='=' read -r key val; do
    [[ -n "$key" && -n "$val" ]] || continue
    sysctl -w "${key}=${val}" >/dev/null 2>&1 || true
  done <<'EOF'
net.ipv4.conf.all.rp_filter=1
net.ipv4.conf.default.rp_filter=1
net.ipv6.conf.all.accept_ra=0
net.ipv6.conf.default.accept_ra=0
net.ipv4.conf.all.accept_redirects=0
net.ipv4.conf.default.accept_redirects=0
net.ipv4.conf.all.send_redirects=0
net.ipv4.icmp_ignore_bogus_error_responses=1
net.ipv4.conf.all.log_martians=1
EOF
}

nexus_perimeter_nftables_edge() {
  [[ "${NEXUS_PERIMETER_APPLY:-0}" == "1" ]] || return 0
  command -v nft >/dev/null 2>&1 || return 0
  local table="${NEXUS_FIREWALL_TABLE:-nexus}"
  nft list table inet "$table" >/dev/null 2>&1 || return 0
  nft list chain inet "$table" perimeter_edge >/dev/null 2>&1 && return 0
  nft add chain inet "$table" perimeter_edge '{ type filter hook input priority 0; policy accept; }' 2>/dev/null || true
  for port in 5353 5355 137 138 1900; do
    nft add rule inet "$table" perimeter_edge udp dport "$port" iifname != "lo" drop 2>/dev/null || true
    nft add rule inet "$table" perimeter_edge tcp dport "$port" iifname != "lo" drop 2>/dev/null || true
  done
}

nexus_perimeter_wol_disable() {
  [[ "${NEXUS_PERIMETER_APPLY:-0}" == "1" ]] || return 0
  command -v ethtool >/dev/null 2>&1 || return 0
  local iface
  for iface in /sys/class/net/*; do
    iface="$(basename "$iface")"
    [[ "$iface" == "lo" ]] && continue
    [[ -d "/sys/class/net/${iface}/device" ]] || continue
    ethtool -s "$iface" wol d 2>/dev/null || true
  done
}

nexus_perimeter_network_lockdown() {
  [[ "${NEXUS_PERIMETER_APPLY:-0}" == "1" ]] || return 0
  [[ "${NEXUS_PERIMETER_NETWORK_LOCKDOWN:-1}" == "1" ]] || return 0
  # shellcheck source=/dev/null
  [[ -f "${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}/lib/network-lockdown.sh" ]] && \
    source "${NEXUS_INSTALL_ROOT}/lib/network-lockdown.sh"
  declare -f nexus_network_lockdown >/dev/null 2>&1 && NEXUS_NETWORK_LOCKDOWN=1 nexus_network_lockdown
}

nexus_perimeter_apply_all() {
  export NEXUS_PERIMETER_APPLY=1
  nexus_perimeter_sysctl_apply
  nexus_perimeter_nftables_edge
  nexus_perimeter_wol_disable
  nexus_perimeter_network_lockdown
}