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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/gatekeeper-enforce.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS v4.0 Packet Permission — block harmful sections only; good flows pass at zero nft cost.

nexus_packet_permission_enabled() {
  local pp
  pp="$(nexus_settings_get NEXUS_PACKET_PERMISSION 2>/dev/null || true)"
  if [[ -n "$pp" ]]; then
    [[ "$pp" == "1" ]]
    return
  fi
  [[ "$(nexus_settings_get NEXUS_GATEKEEPER_STRICT_TRUST 2>/dev/null || echo "${NEXUS_GATEKEEPER_STRICT_TRUST:-1}")" == "1" ]]
}

# Back-compat alias
nexus_gatekeeper_strict_enabled() {
  nexus_packet_permission_enabled
}

nexus_gatekeeper_apply_action() {
  local action="$1" direction="$2" ip="$3" port="$4" reason="$5"
  [[ -n "$ip" ]] || return 0
  nexus_firewall_is_private_ip "$ip" 2>/dev/null && return 0
  nexus_firewall_is_sacred_ip "$ip" 2>/dev/null && return 0
  if declare -f nexus_firewall_is_trusted >/dev/null 2>&1; then
    nexus_firewall_is_trusted "$ip" both 2>/dev/null && return 0
  fi
  case "$action" in
    PERMIT)
      [[ "$port" =~ ^[0-9]+$ && "$port" -gt 0 ]] || return 0
      declare -f nexus_firewall_permit_flow >/dev/null 2>&1 \
        && nexus_firewall_permit_flow "${direction:-out}" "$ip" "$port" "${NEXUS_FIREWALL_PERMIT_FLOW_DURATION:-7200}" "$reason"
      ;;
    BLOCK_SEGMENT)
      [[ "$port" =~ ^[0-9]+$ && "$port" -gt 0 ]] || return 0
      declare -f nexus_firewall_block_flow >/dev/null 2>&1 \
        && nexus_firewall_block_flow "${direction:-out}" "$ip" "$port" "${NEXUS_FIREWALL_BLOCK_DURATION:-86400}" "$reason"
      ;;
    BLOCK_IP)
      nexus_firewall_block_ip in "$ip" "${NEXUS_FIREWALL_BLOCK_DURATION:-86400}" "$reason" || true
      nexus_firewall_block_ip out "$ip" "${NEXUS_FIREWALL_BLOCK_DURATION:-86400}" "$reason" || true
      ;;
  esac
}

nexus_gatekeeper_enforce_strict() {
  nexus_packet_permission_enabled || return 0
  [[ "${NEXUS_CONNECTION_GATEKEEPER:-1}" == "1" ]] || return 0
  command -v pythong >/dev/null 2>&1 || return 0
  declare -f nexus_firewall_block_ip >/dev/null 2>&1 || return 0
  declare -f nexus_firewall_is_sacred_ip >/dev/null 2>&1 || return 0
  declare -f nexus_firewall_is_trusted >/dev/null 2>&1 && nexus_firewall_trust_init

  local py="${NEXUS_INSTALL_ROOT}/lib/packet-permission.py"
  [[ -f "$py" ]] || return 0

  local intent="${NEXUS_STATE_DIR}/connection-intent.json"
  local sig_file="${NEXUS_STATE_DIR}/gatekeeper-enforce.sig"
  local sig=""
  if [[ -s "$intent" ]]; then
    sig="$(pythong -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest()[:20])" "$intent" 2>/dev/null || true)"
  fi
  if [[ -n "$sig" && -f "$sig_file" && "$(cat "$sig_file" 2>/dev/null)" == "$sig" ]]; then
    return 0
  fi
  [[ -n "$sig" ]] && printf '%s' "$sig" >"$sig_file" 2>/dev/null || true

  local permits=0 segments=0 ips=0 line action direction ip port reason scope
  while IFS=$'\t' read -r action direction ip port reason scope; do
    [[ -n "$action" ]] || continue
    nexus_gatekeeper_apply_action "$action" "$direction" "$ip" "$port" "$reason"
    case "$action" in
      PERMIT) permits=$((permits + 1)) ;;
      BLOCK_SEGMENT) segments=$((segments + 1)) ;;
      BLOCK_IP) ips=$((ips + 1)) ;;
    esac
  done < <(
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      pythong "$py" flows 2>/dev/null
  )

  [[ $((permits + segments + ips)) -gt 0 ]] && \
    nexus_log "INFO" "gatekeeper-enforce" "PACKET_PERMISSION permits=${permits} segment_blocks=${segments} ip_blocks=${ips}"
  return 0
}

nexus_packet_enforce_dpi_segments() {
  nexus_packet_permission_enabled || return 0
  [[ "${NEXUS_PACKET_ORACLE:-1}" == "1" ]] || return 0
  command -v pythong >/dev/null 2>&1 || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/packet-permission.py"
  [[ -f "$py" ]] || return 0
  declare -f nexus_gatekeeper_apply_action >/dev/null 2>&1 || return 0

  local segments=0 line action direction ip port reason scope
  while IFS=$'\t' read -r action direction ip port reason scope; do
    [[ "$action" == "BLOCK_SEGMENT" ]] || continue
    nexus_gatekeeper_apply_action "$action" "$direction" "$ip" "$port" "$reason"
    segments=$((segments + 1))
  done < <(
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      pythong "$py" segments 2>/dev/null
  )
  [[ "$segments" -gt 0 ]] && nexus_log "INFO" "gatekeeper-enforce" "DPI_SEGMENT_BLOCKS=${segments}"
  return 0
}