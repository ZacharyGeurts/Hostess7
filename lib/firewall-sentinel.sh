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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/firewall-sentinel.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Firewall Sentinel — NEXUS-owned nftables: good in, bad out, threat-driven blocks.

NEXUS_FIREWALL_TABLE="${NEXUS_FIREWALL_TABLE:-nexus}"
NEXUS_FIREWALL_BLOCKS="${NEXUS_FIREWALL_BLOCKS:-${NEXUS_STATE_DIR}/firewall-blocks.tsv}"
NEXUS_FIREWALL_BLOCK_DURATION="${NEXUS_FIREWALL_BLOCK_DURATION:-86400}"
NEXUS_FIREWALL_BLOCK_FOREVER="${NEXUS_FIREWALL_BLOCK_FOREVER:-3153600000}"
NEXUS_FIREWALL_TEMP_ALLOW_DURATION="${NEXUS_FIREWALL_TEMP_ALLOW_DURATION:-86400}"
NEXUS_FIREWALL_PERMIT_FLOW_DURATION="${NEXUS_FIREWALL_PERMIT_FLOW_DURATION:-7200}"

NEXUS_FIREWALL_BAD_PORTS=(
  4444 5555 1337 31337 6666 6667 9001 9050 1080 3128 4443
)

nexus_firewall_available() {
  command -v nft >/dev/null 2>&1
}

nexus_firewall_is_private_ip() {
  local ip="$1"
  [[ "$ip" =~ ^127\. ]] && return 0
  [[ "$ip" =~ ^10\. ]] && return 0
  [[ "$ip" =~ ^192\.168\. ]] && return 0
  [[ "$ip" =~ ^172\.(1[6-9]|2[0-9]|3[0-1])\. ]] && return 0
  [[ "$ip" =~ ^169\.254\. ]] && return 0
  [[ "$ip" == "::1" || "$ip" =~ ^fe80: || "$ip" =~ ^fd ]] && return 0
  return 1
}

nexus_firewall_parse_ip() {
  local detail="$1" key="$2"
  sed -n "s/.*${key}=\\([^:[:space:]]*\\).*/\\1/p" <<<"$detail" | head -1
}

nexus_firewall_blocks_init() {
  [[ -f "$NEXUS_FIREWALL_BLOCKS" ]] || printf 'ts\tdirection\tip\tport\treason\texpires\n' >"$NEXUS_FIREWALL_BLOCKS"
}

nexus_firewall_backup_ufw() {
  command -v ufw >/dev/null 2>&1 || return 0
  ufw status verbose >"${NEXUS_STATE_DIR}/ufw.backup" 2>/dev/null || true
  chmod 640 "${NEXUS_STATE_DIR}/ufw.backup" 2>/dev/null || true
}

nexus_firewall_disable_ufw() {
  [[ "${NEXUS_FIREWALL_TAKEOVER:-1}" == "1" ]] || return 0
  command -v ufw >/dev/null 2>&1 || return 0
  nexus_firewall_backup_ufw
  ufw --force disable >/dev/null 2>&1 || true
  nexus_log "INFO" "firewall-sentinel" "UFW disabled — NEXUS firewall active"
}

nexus_firewall_apply_base() {
  local port allow_ssh="${NEXUS_FIREWALL_ALLOW_SSH:-0}" bad_ports=""

  for port in "${NEXUS_FIREWALL_BAD_PORTS[@]}"; do
    bad_ports+="${port}, "
  done
  bad_ports="${bad_ports%, }"

  nft list table inet "${NEXUS_FIREWALL_TABLE}" >/dev/null 2>&1 \
    && nft delete table inet "${NEXUS_FIREWALL_TABLE}" 2>/dev/null || true

  local nft_err nft_rc
  nft_err="$(nft -f - 2>&1 <<EOF
table inet ${NEXUS_FIREWALL_TABLE} {
  set block_in {
    type ipv4_addr
    flags timeout
    timeout ${NEXUS_FIREWALL_BLOCK_DURATION}s
  }
  set block_out {
    type ipv4_addr
    flags timeout
    timeout ${NEXUS_FIREWALL_BLOCK_DURATION}s
  }
  set block6_in {
    type ipv6_addr
    flags timeout
    timeout ${NEXUS_FIREWALL_BLOCK_DURATION}s
  }
  set block6_out {
    type ipv6_addr
    flags timeout
    timeout ${NEXUS_FIREWALL_BLOCK_DURATION}s
  }
  set bad_ports {
    type inet_service
    elements = { ${bad_ports} }
  }
  set block_in_ports {
    type inet_service
    flags timeout
    timeout ${NEXUS_FIREWALL_BLOCK_DURATION}s
  }
  set trusted_in {
    type ipv4_addr
  }
  set trusted_out {
    type ipv4_addr
  }
  set temp_allow_out {
    type ipv4_addr
    flags timeout
    timeout ${NEXUS_FIREWALL_TEMP_ALLOW_DURATION}s
  }
  set permit_flow_out {
    type ipv4_addr . inet_service
    flags timeout
    timeout ${NEXUS_FIREWALL_PERMIT_FLOW_DURATION}s
  }
  set block_flow_out {
    type ipv4_addr . inet_service
    flags timeout
    timeout ${NEXUS_FIREWALL_BLOCK_DURATION}s
  }
  set block_flow_in {
    type ipv4_addr . inet_service
    flags timeout
    timeout ${NEXUS_FIREWALL_BLOCK_DURATION}s
  }

  chain input {
    type filter hook input priority -120; policy drop;
    iif "lo" accept
    ct state established,related accept
    ct state invalid drop
    ip saddr @trusted_in accept
    ip saddr . tcp sport @block_flow_in drop
    ip saddr . udp sport @block_flow_in drop
    ip saddr @block_in drop
    ip6 saddr @block6_in drop
    tcp dport @block_in_ports drop
    udp dport @block_in_ports drop
    udp sport 67 udp dport 68 accept
    ip protocol icmp icmp type echo-request limit rate 10/second accept
    ip6 nexthdr icmpv6 icmpv6 type echo-request limit rate 10/second accept
    $( [[ "$allow_ssh" == "1" ]] && echo "tcp dport 22 accept" )
    $( [[ "${NEXUS_DNS_ADMIN_PORTAL:-1}" == "1" ]] && echo "tcp dport { $(echo "${NEXUS_DNS_ADMIN_PORTS:-7,77,777}" | tr -d ' ') } accept comment \"nexus-dns-admin\"" )
    iif != "lo" tcp dport ${NEXUS_THREAT_PANEL_PORT:-9477} drop
    iif != "lo" udp dport ${NEXUS_THREAT_PANEL_PORT:-9477} drop
    counter log prefix "nexus-fw-drop-in: " drop
  }

  chain output {
    type filter hook output priority -120; policy accept;
    ip daddr @trusted_out accept
    ip daddr @temp_allow_out accept
    ip daddr . tcp dport @permit_flow_out accept
    ip daddr . udp dport @permit_flow_out accept
    ip daddr . tcp dport @block_flow_out drop
    ip daddr . udp dport @block_flow_out drop
    ip daddr @block_out drop
    ip6 daddr @block6_out drop
    tcp dport @bad_ports drop
    udp dport @bad_ports drop
  }

  chain forward {
    type filter hook forward priority -120; policy drop;
  }
}
EOF
)"
  nft_rc=$?
  if [[ "$nft_rc" -ne 0 ]]; then
    nexus_log "ALERT" "firewall-sentinel" "FIREWALL_APPLY_FAIL err=${nft_err}"
    return 1
  fi
  return 0
}

nexus_firewall_local_wan_ip() {
  ip -4 route get 1.1.1.1 2>/dev/null | awk '/src/ {print $7; exit}'
}

nexus_firewall_local_gateway_ip() {
  ip -4 route show default 2>/dev/null | awk '/default/ {print $3; exit}'
}

nexus_firewall_is_sacred_ip() {
  local ip="$1" wan gw
  [[ -z "$ip" ]] && return 1
  [[ "$ip" =~ ^127\. ]] && return 0
  [[ "$ip" == "0.0.0.0" ]] && return 0
  wan="$(nexus_firewall_local_wan_ip 2>/dev/null)"
  gw="$(nexus_firewall_local_gateway_ip 2>/dev/null)"
  [[ -n "$wan" && "$ip" == "$wan" ]] && return 0
  [[ -n "$gw" && "$ip" == "$gw" ]] && return 0
  case "$ip" in
    1.1.1.1|1.0.0.1|8.8.8.8|8.8.4.4|9.9.9.9|149.112.112.112) return 0 ;;
  esac
  return 1
}

nexus_firewall_flush_blocks() {
  [[ "${NEXUS_FIREWALL:-1}" == "1" ]] || return 0
  nexus_firewall_available || return 0
  nft flush set inet "${NEXUS_FIREWALL_TABLE}" block_in 2>/dev/null || true
  nft flush set inet "${NEXUS_FIREWALL_TABLE}" block_out 2>/dev/null || true
  nft flush set inet "${NEXUS_FIREWALL_TABLE}" block6_in 2>/dev/null || true
  nft flush set inet "${NEXUS_FIREWALL_TABLE}" block6_out 2>/dev/null || true
  nft flush set inet "${NEXUS_FIREWALL_TABLE}" block_in_ports 2>/dev/null || true
  nft flush set inet "${NEXUS_FIREWALL_TABLE}" permit_flow_out 2>/dev/null || true
  nft flush set inet "${NEXUS_FIREWALL_TABLE}" block_flow_out 2>/dev/null || true
  nft flush set inet "${NEXUS_FIREWALL_TABLE}" block_flow_in 2>/dev/null || true
  printf 'ts\tdirection\tip\tport\treason\texpires\n' >"$NEXUS_FIREWALL_BLOCKS"
  nexus_log "ALERT" "firewall-sentinel" "FIREWALL_FLUSH_ALL — cleared outbound blocks (internet safe)"
}

nexus_firewall_permit_flow() {
  local direction="${1:-out}" ip="$2" port="$3" timeout="${4:-$NEXUS_FIREWALL_PERMIT_FLOW_DURATION}" reason="${5:-permit_flow}"
  [[ "${NEXUS_FIREWALL:-1}" == "1" ]] || return 0
  [[ "$direction" == "out" ]] || return 0
  nexus_firewall_available || return 0
  [[ -n "$ip" && "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ && "$port" =~ ^[0-9]+$ ]] || return 0
  nft add element inet "${NEXUS_FIREWALL_TABLE}" permit_flow_out "{ ${ip} . ${port} timeout ${timeout}s }" 2>/dev/null \
    || nexus_firewall_apply_base
  nft add element inet "${NEXUS_FIREWALL_TABLE}" permit_flow_out "{ ${ip} . ${port} timeout ${timeout}s }" 2>/dev/null || true
  nexus_log "INFO" "firewall-sentinel" "PERMIT_FLOW_OUT ${ip}:${port} reason=${reason}"
}

nexus_firewall_block_flow() {
  local direction="${1:-out}" ip="$2" port="$3" timeout="${4:-$NEXUS_FIREWALL_BLOCK_DURATION}" reason="${5:-segment}"
  [[ "${NEXUS_FIREWALL:-1}" == "1" ]] || return 0
  nexus_firewall_available || return 0
  [[ -n "$ip" && "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ && "$port" =~ ^[0-9]+$ ]] || return 0
  nexus_firewall_is_sacred_ip "$ip" && return 0
  if declare -f nexus_firewall_is_trusted >/dev/null 2>&1; then
    nexus_firewall_is_trusted "$ip" "$direction" && return 0
  fi
  local set="block_flow_${direction}"
  [[ "$direction" == "in" || "$direction" == "out" ]] || direction="out"
  set="block_flow_${direction}"
  nft add element inet "${NEXUS_FIREWALL_TABLE}" "${set}" "{ ${ip} . ${port} timeout ${timeout}s }" 2>/dev/null \
    || nexus_firewall_apply_base
  nft add element inet "${NEXUS_FIREWALL_TABLE}" "${set}" "{ ${ip} . ${port} timeout ${timeout}s }" 2>/dev/null || true
  nexus_firewall_blocks_init
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$direction" "$ip" "$port" "$reason" "$timeout" \
    >>"$NEXUS_FIREWALL_BLOCKS"
  nexus_log "INFO" "firewall-sentinel" "BLOCK_FLOW_${direction^^} ${ip}:${port} reason=${reason}"
}

nexus_firewall_block_ip() {
  local direction="${1:-out}" ip="$2" timeout="${3:-$NEXUS_FIREWALL_BLOCK_DURATION}" reason="${4:-manual}"
  [[ "${NEXUS_FIREWALL:-1}" == "1" ]] || return 0
  if [[ "$direction" == "both" ]]; then
    nexus_firewall_block_ip in "$ip" "$timeout" "$reason"
    nexus_firewall_block_ip out "$ip" "$timeout" "$reason"
    return 0
  fi
  nexus_firewall_available || return 0
  [[ -n "$ip" ]] || return 0
  [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 0
  [[ "$ip" =~ ^127\. ]] && {
    nexus_log "WARN" "firewall-sentinel" "BLOCK_REFUSED localhost ip=${ip} reason=${reason}"
    return 0
  }
  if declare -f nexus_firewall_is_trusted >/dev/null 2>&1; then
    nexus_firewall_is_trusted "$ip" "$direction" && {
      nexus_log "INFO" "firewall-sentinel" "BLOCK_SKIP trusted ip=${ip} dir=${direction}"
      return 0
    }
  fi
  nexus_firewall_is_sacred_ip "$ip" && {
    nexus_log "WARN" "firewall-sentinel" "BLOCK_REFUSED sacred ip=${ip} reason=${reason}"
    return 0
  }
  if [[ "$direction" == "out" ]] && nexus_firewall_is_private_ip "$ip"; then
    return 0
  fi
  local set="block_${direction}"
  nft add element inet "${NEXUS_FIREWALL_TABLE}" "${set}" "{ ${ip} timeout ${timeout}s }" 2>/dev/null \
    || nexus_firewall_apply_base
  nft add element inet "${NEXUS_FIREWALL_TABLE}" "${set}" "{ ${ip} timeout ${timeout}s }" 2>/dev/null || true
  nexus_firewall_blocks_init
  printf '%s\t%s\t%s\t-\t%s\t%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$direction" "$ip" "$reason" "$timeout" \
    >>"$NEXUS_FIREWALL_BLOCKS"
  nexus_log "INFO" "firewall-sentinel" "BLOCK_${direction^^} ip=${ip} reason=${reason}"
}

nexus_firewall_block_port_in() {
  local port="$1" timeout="${2:-$NEXUS_FIREWALL_BLOCK_DURATION}" reason="${3:-threat}"
  [[ "${NEXUS_FIREWALL:-1}" == "1" ]] || return 0
  nexus_firewall_available || return 0
  [[ "$port" =~ ^[0-9]+$ ]] || return 0
  nft add element inet "${NEXUS_FIREWALL_TABLE}" block_in_ports "{ ${port} timeout ${timeout}s }" 2>/dev/null \
    || nexus_firewall_apply_base
  nft add element inet "${NEXUS_FIREWALL_TABLE}" block_in_ports "{ ${port} timeout ${timeout}s }" 2>/dev/null || true
  nexus_log "INFO" "firewall-sentinel" "BLOCK_IN_PORT port=${port} reason=${reason}"
}

nexus_firewall_unblock_ip() {
  local direction="${1:-out}" ip="$2"
  [[ "${NEXUS_FIREWALL:-1}" == "1" ]] || return 0
  if [[ "$direction" == "both" ]]; then
    nexus_firewall_unblock_ip in "$ip"
    nexus_firewall_unblock_ip out "$ip"
    return 0
  fi
  nexus_firewall_available || return 0
  [[ -n "$ip" && "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 0
  local set="block_${direction}"
  nft delete element inet "${NEXUS_FIREWALL_TABLE}" "${set}" "{ ${ip} }" 2>/dev/null || true
  nexus_log "INFO" "firewall-sentinel" "UNBLOCK_${direction^^} ip=${ip}"
}

nexus_firewall_block_ip_forever() {
  nexus_firewall_block_ip "${1:-out}" "$2" "${NEXUS_FIREWALL_BLOCK_FOREVER}" "${3:-block_forever}"
}

nexus_firewall_temp_allow_ip() {
  local direction="${1:-out}" ip="$2" timeout="${3:-$NEXUS_FIREWALL_TEMP_ALLOW_DURATION}"
  [[ "${NEXUS_FIREWALL:-1}" == "1" ]] || return 0
  nexus_firewall_available || return 0
  [[ -n "$ip" && "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 0
  [[ "$direction" == "out" ]] || return 0
  nexus_firewall_unblock_ip out "$ip"
  nft add element inet "${NEXUS_FIREWALL_TABLE}" temp_allow_out "{ ${ip} timeout ${timeout}s }" 2>/dev/null \
    || nexus_firewall_apply_base
  nft add element inet "${NEXUS_FIREWALL_TABLE}" temp_allow_out "{ ${ip} timeout ${timeout}s }" 2>/dev/null || true
  nexus_log "INFO" "firewall-sentinel" "TEMP_ALLOW_OUT ip=${ip} timeout=${timeout}s"
}

nexus_firewall_is_blocked() {
  local direction="${1:-out}" ip="$2"
  [[ -n "$ip" ]] || return 1
  nexus_firewall_blocks_init
  awk -F'\t' -v ip="$ip" -v dir="$direction" '
    NR > 1 && $3 == ip && ($2 == dir || $2 == "both") { found = 1 }
    END { exit(found ? 0 : 1) }
  ' "$NEXUS_FIREWALL_BLOCKS" 2>/dev/null
}

nexus_firewall_blocks_json() {
  nexus_firewall_blocks_init
  local first=1 line ts direction ip port reason expires
  printf '['
  while IFS=$'\t' read -r ts direction ip port reason expires; do
    [[ -n "$ip" ]] || continue
    [[ "$first" -eq 1 ]] || printf ','
    first=0
    printf '{"ts":"%s","direction":"%s","ip":"%s","port":"%s","reason":"%s","expires":"%s"}' \
      "$ts" "$direction" "$ip" "${port:-}" "${reason:-}" "${expires:-}"
  done < <(tail -n +2 "$NEXUS_FIREWALL_BLOCKS" 2>/dev/null)
  printf ']'
}

nexus_firewall_unblock_port_in() {
  local port="$1"
  [[ "${NEXUS_FIREWALL:-1}" == "1" ]] || return 0
  nexus_firewall_available || return 0
  [[ "$port" =~ ^[0-9]+$ ]] || return 0
  nft delete element inet "${NEXUS_FIREWALL_TABLE}" block_in_ports "{ ${port} }" 2>/dev/null || true
  nexus_log "INFO" "firewall-sentinel" "UNBLOCK_IN_PORT port=${port}"
}

nexus_firewall_on_threat() {
  local vector="$1" severity="$2" detail="$3"
  [[ "${NEXUS_FIREWALL:-1}" == "1" ]] || return 0
  [[ "${NEXUS_FIREWALL_AUTO_BLOCK:-0}" == "1" ]] || return 0
  if declare -f nexus_threat_is_meta_vector >/dev/null 2>&1; then
    nexus_threat_is_meta_vector "$vector" && return 0
  fi
  local ip port
  ip="$(nexus_firewall_parse_ip "$detail" "dst")"
  [[ -z "$ip" ]] && ip="$(nexus_firewall_parse_ip "$detail" "ip")"
  if [[ -n "$ip" ]] && declare -f nexus_firewall_is_trusted >/dev/null 2>&1 \
    && nexus_firewall_is_trusted "$ip" "both"; then
    return 0
  fi
  case "$vector" in
    C2_CORRELATION|RST_FLOOD) return 0 ;;
    ARP_SPOOF|PACKET_INJECTION|GATEWAY_SHIFT|CONN_HIJACK|AI_ROGUE_INFRA)
      ip="$(nexus_firewall_parse_ip "$detail" "ip")"
      [[ -n "$ip" ]] && nexus_firewall_block_ip in "$ip" "$NEXUS_FIREWALL_BLOCK_DURATION" "$vector"
      ;;
    EGRESS_BEACON|EGRESS_TMP_BINARY|AI_BEACON_PRECISION|AI_LOLBIN_CHAIN|AI_EXFIL_SHAPE|AI_AUTOSCAN|AI_ML_C2_STACK|AI_PHISH_FRAUD)
      ip="$(nexus_firewall_parse_ip "$detail" "dst")"
      [[ -n "$ip" ]] && nexus_firewall_block_ip out "$ip" "$NEXUS_FIREWALL_BLOCK_DURATION" "$vector"
      ;;
    MITM_LISTENER|LISTENER_SURGE)
      port="$(sed -n 's/.*bind=[^:]*:\([0-9]*\).*/\1/p' <<<"$detail")"
      [[ -z "$port" ]] && port="$(sed -n 's/.*new_listener=[^:]*:\([0-9]*\).*/\1/p' <<<"$detail")"
      [[ -n "$port" && "$port" != "22" && "$port" != "53" && "$port" != "631" ]] && \
        nexus_firewall_block_port_in "$port" "$NEXUS_FIREWALL_BLOCK_DURATION" "$vector"
      ;;
  esac
}

nexus_firewall_takeover() {
  [[ "${NEXUS_FIREWALL:-1}" == "1" ]] || return 0
  nexus_firewall_available || {
    nexus_log "WARN" "firewall-sentinel" "nft missing — install nftables"
    return 1
  }
  nexus_firewall_disable_ufw
  nexus_firewall_apply_base || return 1
  nexus_firewall_blocks_init
  echo "active=1" >"${NEXUS_STATE_DIR}/firewall.state"
  chmod 640 "${NEXUS_STATE_DIR}/firewall.state" 2>/dev/null || true
  chown root:nexus "${NEXUS_STATE_DIR}/firewall.state" 2>/dev/null || true
  if declare -f nexus_firewall_trust_sync_from_memory >/dev/null 2>&1; then
    nexus_firewall_trust_sync_from_memory
    nexus_firewall_trust_reload
  fi
  nexus_log "INFO" "firewall-sentinel" "FIREWALL_TAKEOVER active table=${NEXUS_FIREWALL_TABLE}"
  return 0
}

nexus_firewall_verify() {
  [[ "${NEXUS_FIREWALL:-1}" == "1" ]] || return 0
  nexus_firewall_available || return 0
  nft list table inet "${NEXUS_FIREWALL_TABLE}" >/dev/null 2>&1 || nexus_firewall_takeover
}

nexus_firewall_status() {
  if [[ "${NEXUS_FIREWALL:-1}" != "1" ]]; then
    echo "firewall=disabled"
    return
  fi
  if [[ -r "${NEXUS_STATE_DIR}/firewall.state" ]] && grep -q '^active=1' "${NEXUS_STATE_DIR}/firewall.state" 2>/dev/null; then
    echo "firewall=active"
    echo "table=${NEXUS_FIREWALL_TABLE}"
    echo "blocks=$(tail -n +2 "$NEXUS_FIREWALL_BLOCKS" 2>/dev/null | wc -l | tr -d ' ')"
  elif nft list table inet "${NEXUS_FIREWALL_TABLE}" >/dev/null 2>&1; then
    echo "firewall=active"
    echo "table=${NEXUS_FIREWALL_TABLE}"
    echo "blocks=$(tail -n +2 "$NEXUS_FIREWALL_BLOCKS" 2>/dev/null | wc -l | tr -d ' ')"
  else
    echo "firewall=missing"
  fi
}