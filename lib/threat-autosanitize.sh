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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/threat-autosanitize.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Threat autosanitize — auto-block on vector detect; panel undo with action IDs.

NEXUS_AUTOSANITIZE_STATE="${NEXUS_AUTOSANITIZE_STATE:-${NEXUS_STATE_DIR}/autosanitize.json}"
NEXUS_SANITIZE_ACTIONS="${NEXUS_SANITIZE_ACTIONS:-${NEXUS_STATE_DIR}/sanitize-actions.tsv}"
NEXUS_SANITIZE_UNDO_QUEUE="${NEXUS_SANITIZE_UNDO_QUEUE:-${NEXUS_STATE_DIR}/sanitize-undo.queue}"

nexus_autosanitize_enabled() {
  [[ "${NEXUS_AUTOSANITIZE:-1}" == "1" ]]
}

nexus_autosanitize_init() {
  mkdir -p "$(dirname "$NEXUS_SANITIZE_ACTIONS")" 2>/dev/null || true
  [[ -f "$NEXUS_SANITIZE_ACTIONS" ]] || printf 'id\tts\tvector\tseverity\ttarget\ttarget_type\taction\tundone\n' >"$NEXUS_SANITIZE_ACTIONS"
  if [[ ! -f "$NEXUS_AUTOSANITIZE_STATE" ]]; then
    printf '{"enabled":true,"updated":"%s"}\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >"$NEXUS_AUTOSANITIZE_STATE"
    chmod 640 "$NEXUS_AUTOSANITIZE_STATE" 2>/dev/null || true
    chown root:nexus "$NEXUS_AUTOSANITIZE_STATE" 2>/dev/null || true
  fi
}

nexus_autosanitize_set_enabled() {
  local on="${1:-1}"
  nexus_autosanitize_init
  local ts
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)"
  if [[ "$on" == "1" || "$on" == "true" || "$on" == "on" ]]; then
    printf '{"enabled":true,"updated":"%s"}\n' "$ts" >"${NEXUS_AUTOSANITIZE_STATE}.tmp" \
      && mv "${NEXUS_AUTOSANITIZE_STATE}.tmp" "$NEXUS_AUTOSANITIZE_STATE"
    nexus_log "INFO" "autosanitize" "AUTOSANITIZE_ON"
  else
    printf '{"enabled":false,"updated":"%s"}\n' "$ts" >"${NEXUS_AUTOSANITIZE_STATE}.tmp" \
      && mv "${NEXUS_AUTOSANITIZE_STATE}.tmp" "$NEXUS_AUTOSANITIZE_STATE"
    nexus_log "INFO" "autosanitize" "AUTOSANITIZE_OFF"
  fi
  chmod 640 "$NEXUS_AUTOSANITIZE_STATE" 2>/dev/null || true
}

nexus_autosanitize_is_on() {
  nexus_autosanitize_init
  grep -q '"enabled"[[:space:]]*:[[:space:]]*true' "$NEXUS_AUTOSANITIZE_STATE" 2>/dev/null
}

nexus_autosanitize_make_id() {
  local vector="$1" target="$2"
  printf 'san-%s-%s' "$(date +%s)" "$(printf '%s' "${vector}_${target}" | md5sum 2>/dev/null | cut -c1-8 || echo rand)"
}

nexus_autosanitize_on_threat() {
  local vector="$1" severity="$2" detail="$3"
  nexus_autosanitize_init
  nexus_autosanitize_is_on || return 0

  local id ts target target_type action ip port
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)"
  target=""
  target_type="none"
  action="log"

  case "$vector" in
    ARP_SPOOF|PACKET_INJECTION|GATEWAY_SHIFT|CONN_HIJACK)
      ip="$(nexus_firewall_parse_ip "$detail" "ip")"
      if [[ -n "$ip" ]]; then
        target="$ip"
        target_type="ip_in"
        action="block_ip_in"
      fi
      ;;
    EGRESS_BEACON|EGRESS_TMP_BINARY|C2_CORRELATION|RST_FLOOD|AI_BEACON_PRECISION|AI_LOLBIN_CHAIN|AI_EXFIL_SHAPE|AI_AUTOSCAN|AI_ML_C2_STACK|AI_PHISH_FRAUD)
      ip="$(nexus_firewall_parse_ip "$detail" "dst")"
      if [[ -n "$ip" ]]; then
        target="$ip"
        target_type="ip_out"
        action="block_ip_out"
      fi
      ;;
    DNS_POISON|DNS_TUNNEL|DDOS_FLOOD|AI_ROGUE_INFRA|AI_DNS_TUNNEL)
      ip="$(nexus_firewall_parse_ip "$detail" "ip")"
      [[ -z "$ip" ]] && ip="$(nexus_firewall_parse_ip "$detail" "src")"
      [[ -z "$ip" ]] && ip="$(sed -n 's/.*client=\([^[:space:]]*\).*/\1/p' <<<"$detail" | cut -d: -f1)"
      if [[ -n "$ip" ]]; then
        target="$ip"
        target_type="ip_in"
        action="block_ip_in"
      fi
      declare -f nexus_field_dns_enforce_cycle >/dev/null 2>&1 && nexus_field_dns_enforce_cycle || true
      ;;
    MITM_LISTENER|LISTENER_SURGE)
      port="$(sed -n 's/.*bind=[^:]*:\([0-9]*\).*/\1/p' <<<"$detail")"
      [[ -z "$port" ]] && port="$(sed -n 's/.*new_listener=[^:]*:\([0-9]*\).*/\1/p' <<<"$detail")"
      if [[ -n "$port" ]]; then
        target="$port"
        target_type="port_in"
        action="block_port_in"
      fi
      ;;
    *)
      target="$(printf '%s' "$detail" | head -c 80)"
      target_type="detail"
      action="annotate"
      ;;
  esac

  id="$(nexus_autosanitize_make_id "$vector" "$target")"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t0\n' \
    "$id" "$ts" "$vector" "$severity" "$target" "$target_type" "$action" >>"$NEXUS_SANITIZE_ACTIONS"
  chmod 640 "$NEXUS_SANITIZE_ACTIONS" 2>/dev/null || true
  if [[ "$action" == block_ip_in || "$action" == block_ip_out || "$action" == block_port_in ]]; then
    # shellcheck source=/dev/null
    [[ -f "${NEXUS_INSTALL_ROOT}/lib/firewall-sentinel.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/firewall-sentinel.sh"
    case "$action" in
      block_ip_in)  nexus_firewall_block_ip in "$target" "${NEXUS_FIREWALL_BLOCK_DURATION:-86400}" "$vector" ;;
      block_ip_out) nexus_firewall_block_ip out "$target" "${NEXUS_FIREWALL_BLOCK_DURATION:-86400}" "$vector" ;;
      block_port_in) nexus_firewall_block_port_in "$target" "${NEXUS_FIREWALL_BLOCK_DURATION:-86400}" "$vector" ;;
    esac
  fi
  nexus_log "INFO" "autosanitize" "SANITIZE id=${id} vector=${vector} target=${target} action=${action}"
}

nexus_autosanitize_recent() {
  local limit="${1:-30}"
  tail -n "$((limit + 1))" "$NEXUS_SANITIZE_ACTIONS" 2>/dev/null | tail -n +2
}

nexus_autosanitize_undo() {
  local id="$1"
  [[ -n "$id" ]] || return 1
  nexus_autosanitize_init

  local line target_type target action undone
  line="$(awk -F'\t' -v id="$id" '$1 == id { print; exit }' "$NEXUS_SANITIZE_ACTIONS" 2>/dev/null)"
  [[ -n "$line" ]] || return 1

  IFS=$'\t' read -r _ _ _ _ target target_type action undone <<<"$line"
  [[ "$undone" == "1" ]] && return 0

  # shellcheck source=/dev/null
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/firewall-sentinel.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/firewall-sentinel.sh"

  case "$action" in
    block_ip_in)  nexus_firewall_unblock_ip in "$target" ;;
    block_ip_out) nexus_firewall_unblock_ip out "$target" ;;
    block_port_in) nexus_firewall_unblock_port_in "$target" ;;
    *) ;;
  esac

  local tmp="${NEXUS_SANITIZE_ACTIONS}.tmp"
  awk -F'\t' -v id="$id" 'BEGIN {OFS="\t"} $1 == id { $8 = "1" } { print }' \
    "$NEXUS_SANITIZE_ACTIONS" >"$tmp" 2>/dev/null \
    && mv "$tmp" "$NEXUS_SANITIZE_ACTIONS"
  nexus_log "INFO" "autosanitize" "UNDO id=${id} target=${target} action=${action}"
  return 0
}

nexus_autosanitize_json_actions() {
  local limit="${1:-25}"
  nexus_autosanitize_init
  local first=1 line id ts vector severity target target_type action undone esc
  printf '['
  while IFS=$'\t' read -r id ts vector severity target target_type action undone; do
    [[ -n "$id" ]] || continue
    esc="$(printf '%s' "$target" | sed 's/\\/\\\\/g; s/"/\\"/g')"
    [[ "$first" -eq 1 ]] || printf ','
    first=0
    printf '{"id":"%s","ts":"%s","vector":"%s","severity":"%s","target":"%s","target_type":"%s","action":"%s","undone":%s}' \
      "$id" "$ts" "$vector" "$severity" "$esc" "$target_type" "$action" \
      "$( [[ "$undone" == "1" ]] && echo true || echo false )"
  done <<<"$(nexus_autosanitize_recent "$limit")"
  printf ']'
}