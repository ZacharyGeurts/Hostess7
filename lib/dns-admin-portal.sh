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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/dns-admin-portal.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Hostess 7 DNS Admin Portal — ports 7, 77, 777 (information only).

nexus_dns_admin_ports() {
  printf '%s\n' "${NEXUS_DNS_ADMIN_PORTS:-7,77,777}"
}

nexus_dns_admin_firewall_permit() {
  [[ "${NEXUS_DNS_ADMIN_PORTAL:-1}" == "1" ]] || return 0
  command -v nft >/dev/null 2>&1 || return 0
  local ports="${NEXUS_DNS_ADMIN_PORTS:-7,77,777}"
  ports="${ports// /}"
  [[ -n "$ports" ]] || return 0
  if nft list chain inet "${NEXUS_FIREWALL_TABLE:-nexus}" input 2>/dev/null | grep -q 'nexus-dns-admin'; then
    return 0
  fi
  nft add rule inet "${NEXUS_FIREWALL_TABLE:-nexus}" input \
    tcp dport "{ ${ports} }" accept comment "nexus-dns-admin" 2>/dev/null \
    && nexus_log "INFO" "dns-admin-portal" "firewall permit tcp {${ports}} (DNS admin read-only)" \
    || nexus_log "WARN" "dns-admin-portal" "firewall permit skipped (may need root)"
}

nexus_dns_admin_publish() {
  [[ "${NEXUS_DNS_ADMIN_PORTAL:-1}" == "1" ]] || return 0
  command -v pythong >/dev/null 2>&1 || return 0
  local erpy="${NEXUS_INSTALL_ROOT}/lib/equipment-room-field.py"
  [[ -f "$erpy" ]] || return 0
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$erpy" build >/dev/null 2>&1 || true
}

nexus_dns_admin_stop_stale() {
  local pidf="${NEXUS_STATE_DIR}/dns-admin-portal.pid"
  if [[ -s "$pidf" ]]; then
    local oldpid
    oldpid="$(tr -dc '0-9' <"$pidf" 2>/dev/null || true)"
    [[ -n "$oldpid" ]] && kill "$oldpid" 2>/dev/null || true
  fi
  pkill -f 'dns-admin-portal.py serve' 2>/dev/null || true
  local ports="${NEXUS_DNS_ADMIN_PORTS:-7,77,777}"
  if command -v fuser >/dev/null 2>&1; then
    local p
    for p in ${ports//,/ }; do
      fuser -k "${p}/tcp" 2>/dev/null || true
    done
  fi
  sleep 1
}

nexus_dns_admin_serve_loop() {
  [[ "${NEXUS_DNS_ADMIN_PORTAL:-1}" == "1" ]] || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/dns-admin-portal.py"
  [[ -f "$py" ]] || return 0
  nexus_dns_admin_stop_stale
  nexus_dns_admin_firewall_permit
  while true; do
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      NEXUS_DNS_ADMIN_PORTS="${NEXUS_DNS_ADMIN_PORTS:-7,77,777}" \
      pythong "$py" serve 2>/dev/null || true
    nexus_dns_admin_stop_stale
    sleep 5
  done
}

nexus_dns_admin_status_json() {
  local py="${NEXUS_INSTALL_ROOT}/lib/dns-admin-portal.py"
  if [[ -f "$py" ]]; then
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      pythong "$py" status 2>/dev/null && return 0
  fi
  printf '{"schema":"dns-admin-portal/v1","running":false,"ports":[7,77,777]}'
}