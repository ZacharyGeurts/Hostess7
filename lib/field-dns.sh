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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-dns.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS Field DNS — truth resolver publish, multipoint local capture, resolv override.

nexus_field_dns_publish() {
  [[ "${NEXUS_FIELD_DNS:-1}" == "1" ]] || return 0
  command -v pythong >/dev/null 2>&1 || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/field-dns.py"
  [[ -f "$py" ]] || return 0
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$py" build >/dev/null 2>&1 || true
  local eg="${NEXUS_INSTALL_ROOT}/lib/dns-egress-integrity.py"
  [[ -f "$eg" ]] && NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$eg" build >/dev/null 2>&1 || true
  local tg="${NEXUS_INSTALL_ROOT}/lib/dns-threat-guard.py"
  [[ -f "$tg" ]] && NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$tg" build >/dev/null 2>&1 || true
  local dh="${NEXUS_INSTALL_ROOT}/lib/field-dhcp.py"
  [[ -f "$dh" ]] && NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$dh" build >/dev/null 2>&1 || true
  local to="${NEXUS_INSTALL_ROOT}/lib/dns-service-takeover.py"
  [[ -f "$to" ]] && NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$to" build >/dev/null 2>&1 || true
  local mid="${NEXUS_INSTALL_ROOT}/lib/dns-multipoint-identity.py"
  [[ -f "$mid" ]] && NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$mid" build >/dev/null 2>&1 || true
  local inf="${NEXUS_INSTALL_ROOT}/lib/dns-internet-field.py"
  [[ -f "$inf" ]] && NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$inf" build >/dev/null 2>&1 || true
  local ntp="${NEXUS_INSTALL_ROOT}/lib/field-ntp-2026.py"
  [[ -f "$ntp" ]] && NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$ntp" build >/dev/null 2>&1 || true
  local st="${NEXUS_INSTALL_ROOT}/lib/sovereign-time.py"
  [[ -f "$st" ]] && NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$st" status >/dev/null 2>&1 || true
  local gate="${NEXUS_INSTALL_ROOT}/lib/field-sovereign-gate.py"
  [[ -f "$gate" ]] && NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$gate" json >/dev/null 2>&1 || true
  local fs="${NEXUS_INSTALL_ROOT}/lib/field-services-2026.py"
  [[ -f "$fs" ]] && NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$fs" build >/dev/null 2>&1 || true
  local sync="${NEXUS_INSTALL_ROOT}/lib/field-sovereign-sync.py"
  [[ -f "$sync" ]] && NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$sync" mirror >/dev/null 2>&1 && \
    pythong "$sync" json >/dev/null 2>&1 || true
}

nexus_dns_internet_pull_loop() {
  [[ "${NEXUS_DNS_INTERNET_PULL:-1}" == "1" ]] || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/dns-internet-field.py"
  [[ -f "$py" ]] || return 0
  while true; do
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      pythong "$py" pull >/dev/null 2>&1 || true
    sleep "${NEXUS_DNS_INTERNET_PULL_INTERVAL:-3600}"
  done
}

nexus_field_dns_json() {
  if declare -f nexus_field_dns_publish >/dev/null 2>&1; then
    nexus_field_dns_publish
  fi
  local py="${NEXUS_INSTALL_ROOT}/lib/field-dns.py"
  local cache="${NEXUS_STATE_DIR}/field-dns-panel.json"
  if [[ -f "$py" ]]; then
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      pythong "$py" json 2>/dev/null && return 0
  fi
  if [[ -s "$cache" ]]; then
    pythong -c "import json,sys; json.dump(json.load(open(sys.argv[1])), sys.stdout)" "$cache" 2>/dev/null
    return 0
  fi
  printf '{"schema":"field-dns/v2","running":false,"rfc_matrix":[],"legal_framework":[],"zones":[]}'
}

nexus_field_dns_takeover_cycle() {
  [[ "${NEXUS_FIELD_DNS:-1}" == "1" ]] || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/dns-service-takeover.py"
  [[ -f "$py" ]] || return 0
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$py" evaluate >/dev/null 2>&1 || true
  local phase
  phase="$(NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$py" phase 2>/dev/null || echo observing)"
  if [[ "$phase" == "primary" ]]; then
    declare -f nexus_field_dns_enforce_resolv >/dev/null 2>&1 && nexus_field_dns_enforce_resolv || true
    declare -f nexus_field_dns_local_capture >/dev/null 2>&1 && nexus_field_dns_local_capture || true
  fi
}

nexus_field_dns_serve_loop() {
  [[ "${NEXUS_FIELD_DNS:-1}" == "1" ]] || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/field-dns.py"
  [[ -f "$py" ]] || return 0
  declare -f nexus_field_dns_takeover_cycle >/dev/null 2>&1 && nexus_field_dns_takeover_cycle || true
  while true; do
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      NEXUS_FIELD_DNS_BINDS_IPV4="${NEXUS_FIELD_DNS_BINDS_IPV4:-127.0.0.1}" \
      NEXUS_FIELD_DNS_BINDS_IPV6="${NEXUS_FIELD_DNS_BINDS_IPV6:-::1}" \
      pythong "$py" serve 2>/dev/null || true
    sleep 5
  done
}

nexus_field_dns_enforce_resolv() {
  [[ "${NEXUS_FIELD_DNS_ENFORCE_RESOLV:-1}" == "1" ]] || return 0
  local to="${NEXUS_INSTALL_ROOT}/lib/dns-service-takeover.py"
  if [[ -f "$to" ]]; then
    local ok
    ok="$(NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      pythong "$to" can-enforce-resolv 2>/dev/null || echo 0)"
    [[ "$ok" == "1" ]] || return 0
  fi
  local port="${NEXUS_FIELD_DNS_PORT:-53}"
  local stub="${NEXUS_STATE_DIR}/resolv.conf.nexus-stub"
  local backup="${NEXUS_STATE_DIR}/resolv.conf.nexus-backup"
  if [[ ! -f "$backup" && -f /etc/resolv.conf && ! -L /etc/resolv.conf ]]; then
    cp -a /etc/resolv.conf "$backup" 2>/dev/null || true
  elif [[ ! -f "$backup" && -L /etc/resolv.conf ]]; then
    cp -a "$(readlink -f /etc/resolv.conf 2>/dev/null || echo /etc/resolv.conf)" "$backup" 2>/dev/null || true
  fi
  {
    echo "# NEXUS Truth DNS — all local queries use our resolver (RFC 1035, RFC 6761, RFC 9520)"
    echo "# User DNS settings overridden — multipoint secure identification"
    echo "nameserver 127.0.0.1"
    echo "nameserver ::1"
    echo "options edns0 trust-ad single-request-reopen"
    echo "# NEXUS_FIELD_DNS_PORT=${port}"
    echo "# NEXUS_FIELD_DNS_BINDS=${NEXUS_FIELD_DNS_BINDS_IPV4:-127.0.0.1,127.0.0.53}"
  } >"$stub"
  if [[ "$(id -u)" -eq 0 ]]; then
    if [[ "${NEXUS_FIELD_DNS_BREAK_RESOLV_SYMLINK:-1}" == "1" && -L /etc/resolv.conf ]]; then
      rm -f /etc/resolv.conf 2>/dev/null || true
    fi
    cp -f "$stub" /etc/resolv.conf 2>/dev/null || true
    chmod 644 /etc/resolv.conf 2>/dev/null || true
  fi
  nexus_log "INFO" "field-dns" "resolv override active (127.0.0.1 + ::1 truth resolver)"
}

nexus_field_dns_foreign_ips() {
  local py="${NEXUS_INSTALL_ROOT}/lib/dns-planetary-security.py"
  if [[ -f "$py" ]]; then
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      pythong "$py" foreign-ips 2>/dev/null && return 0
  fi
  printf '%s\n' '{"ipv4":["8.8.8.8","8.8.4.4","1.1.1.1","1.0.0.1","9.9.9.9","71.10.216.1","71.10.216.2"],"ipv6":["2001:4860:4860::8888","2001:4860:4860::8844","2606:4700:4700::1111","2606:4700:4700::1001","2620:fe::fe","2620:fe::9"]}'
}

nexus_field_dns_local_capture() {
  [[ "${NEXUS_FIELD_DNS_LOCAL_CAPTURE:-1}" == "1" ]] || return 0
  command -v nft >/dev/null 2>&1 || return 0
  local port="${NEXUS_FIELD_DNS_PORT:-53}"
  local table="${NEXUS_FIREWALL_TABLE:-nexus}"
  if nft list chain inet "$table" output 2>/dev/null | grep -q 'nexus-dns-local'; then
    return 0
  fi
  # Block egress DNS to foreign resolvers — never add untrusted (RFC 9520)
  local foreign_json foreign4 foreign6
  foreign_json="$(nexus_field_dns_foreign_ips)"
  foreign4="$(printf '%s' "$foreign_json" | pythong -c 'import json,sys; d=json.load(sys.stdin); print(", ".join(d.get("ipv4") or []))' 2>/dev/null || true)"
  foreign6="$(printf '%s' "$foreign_json" | pythong -c 'import json,sys; d=json.load(sys.stdin); print(", ".join(d.get("ipv6") or []))' 2>/dev/null || true)"
  foreign4="${foreign4:-8.8.8.8, 8.8.4.4, 1.1.1.1, 1.0.0.1, 9.9.9.9, 71.10.216.1, 71.10.216.2}"
  if [[ -n "$foreign4" ]]; then
    nft add rule inet "$table" output \
      ip daddr "{ ${foreign4} }" udp dport "${port}" drop comment "nexus-dns-local" 2>/dev/null || true
    nft add rule inet "$table" output \
      ip daddr "{ ${foreign4} }" tcp dport "${port}" drop comment "nexus-dns-local" 2>/dev/null || true
  fi
  if [[ -n "$foreign6" ]]; then
    nft add rule inet "$table" output \
      ip6 daddr "{ ${foreign6} }" udp dport "${port}" drop comment "nexus-dns-local-v6" 2>/dev/null || true
    nft add rule inet "$table" output \
      ip6 daddr "{ ${foreign6} }" tcp dport "${port}" drop comment "nexus-dns-local-v6" 2>/dev/null || true
  fi
  nft add rule inet "$table" output \
    udp dport 853 drop comment "nexus-dns-local-dot" 2>/dev/null || true
  # DDoS immunity — rate-limit DNS ingress to loopback resolver (IPv4 + IPv6)
  nft add rule inet "$table" input \
    ip daddr 127.0.0.1 udp dport "${port}" limit rate 120/second burst 60 packets accept comment "nexus-dns-ddos-in" 2>/dev/null || true
  nft add rule inet "$table" input \
    ip daddr 127.0.0.1 udp dport "${port}" drop comment "nexus-dns-ddos-drop" 2>/dev/null || true
  nft add rule inet "$table" input \
    ip6 daddr ::1 udp dport "${port}" limit rate 120/second burst 60 packets accept comment "nexus-dns-ddos-in6" 2>/dev/null || true
  nft add rule inet "$table" input \
    ip6 daddr ::1 udp dport "${port}" drop comment "nexus-dns-ddos-drop6" 2>/dev/null || true
  nexus_log "INFO" "field-dns" "local DNS capture — foreign resolver egress blocked (IPv4+IPv6) · DDoS rate limit active"
}

nexus_field_dhcp_serve_loop() {
  [[ "${NEXUS_FIELD_DHCP:-1}" == "1" ]] || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/field-dhcp.py"
  [[ -f "$py" ]] || return 0
  while true; do
    local ok=1
    local to="${NEXUS_INSTALL_ROOT}/lib/dns-service-takeover.py"
    if [[ -f "$to" ]]; then
      ok="$(NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
        pythong "$to" can-serve-dhcp 2>/dev/null || echo 0)"
    fi
    if [[ "$ok" == "1" ]]; then
      NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
        pythong "$py" serve 2>/dev/null || true
    else
      NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
        pythong "$py" build >/dev/null 2>&1 || true
      sleep 15
    fi
    sleep 5
  done
}

nexus_field_local_connect() {
  [[ "${NEXUS_FIELD_LOCAL_DNS_CONNECT:-1}" == "1" ]] || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/field-local-dns-connect.py"
  [[ -f "$py" ]] || return 0
  local runner="pythong"
  command -v pythong >/dev/null 2>&1 || runner="python3"
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    "$runner" "$py" connect >/dev/null 2>&1 || true
}

nexus_field_local_connect_loop() {
  [[ "${NEXUS_FIELD_LOCAL_DNS_CONNECT:-1}" == "1" ]] || return 0
  while true; do
    declare -f nexus_field_local_connect >/dev/null 2>&1 && nexus_field_local_connect || true
    sleep "${NEXUS_FIELD_LOCAL_CONNECT_INTERVAL:-8}"
  done
}

nexus_field_services_boot() {
  [[ "${NEXUS_FIELD_DNS:-1}" == "1" ]] || return 0
  declare -f nexus_field_dns_publish >/dev/null 2>&1 && nexus_field_dns_publish || true
  if ! pgrep -f 'field-dns.py serve' >/dev/null 2>&1; then
    nohup env NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      bash -c 'source "'"${NEXUS_INSTALL_ROOT}"'/lib/field-dns.sh" && nexus_field_dns_serve_loop' \
      >>"${NEXUS_STATE_DIR}/field-dns-serve.log" 2>&1 &
  fi
  if [[ "${NEXUS_FIELD_DHCP:-1}" == "1" ]] && ! pgrep -f 'field-dhcp.py serve' >/dev/null 2>&1; then
    nohup env NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      bash -c 'source "'"${NEXUS_INSTALL_ROOT}"'/lib/field-dns.sh" && nexus_field_dhcp_serve_loop' \
      >>"${NEXUS_STATE_DIR}/field-dhcp-serve.log" 2>&1 &
  fi
  if [[ "${NEXUS_FIELD_LOCAL_DNS_CONNECT:-1}" == "1" ]] && ! pgrep -f 'nexus_field_local_connect_loop' >/dev/null 2>&1; then
    nohup env NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      bash -c 'source "'"${NEXUS_INSTALL_ROOT}"'/lib/field-dns.sh" && nexus_field_local_connect_loop' \
      >>"${NEXUS_STATE_DIR}/field-local-connect.log" 2>&1 &
  fi
  declare -f nexus_field_local_connect >/dev/null 2>&1 && nexus_field_local_connect || true
}

nexus_field_dns_enforce_cycle() {
  [[ "${NEXUS_FIELD_DNS:-1}" == "1" ]] || return 0
  declare -f nexus_field_dns_takeover_cycle >/dev/null 2>&1 && nexus_field_dns_takeover_cycle || true
  declare -f nexus_field_dns_publish >/dev/null 2>&1 && nexus_field_dns_publish || true
  declare -f nexus_field_local_connect >/dev/null 2>&1 && nexus_field_local_connect || true
}

nexus_sovereign_time_serve_loop() {
  [[ "${NEXUS_SOVEREIGN_TIME:-1}" == "1" ]] || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/sovereign-time.py"
  [[ -f "$py" ]] || return 0
  while true; do
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      NEXUS_SOVEREIGN_TIME_BIND="${NEXUS_SOVEREIGN_TIME_BIND:-127.0.0.1}" \
      pythong "$py" serve 2>/dev/null || true
    sleep 5
  done
}

nexus_field_ntp_serve_loop() {
  [[ "${NEXUS_FIELD_NTP:-1}" == "1" ]] || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/field-ntp-2026.py"
  [[ -f "$py" ]] || return 0
  while true; do
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      NEXUS_FIELD_NTP_BIND="${NEXUS_FIELD_NTP_BIND:-127.0.0.1}" \
      NEXUS_SOVEREIGN_TIME_FIRST="${NEXUS_SOVEREIGN_TIME_FIRST:-1}" \
      pythong "$py" serve 2>/dev/null || true
    sleep 5
  done
}