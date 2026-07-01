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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/threat-vectors.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Threat vectors — AMOURANTHRTX field catalog (TTP clustering, corroboration).
# AMOURANTHRTX: GPL v3 or commercial (not MIT-free). NEXUS-Shield: MIT.

NEXUS_THREAT_VECTORS_DB="${NEXUS_THREAT_VECTORS_DB:-${NEXUS_STATE_DIR}/threat-vectors.tsv}"
NEXUS_FIELD_NOISE_RATIO="${NEXUS_FIELD_NOISE_RATIO:-0.94}"
NEXUS_FIELD_TRUTH_RATIO="${NEXUS_FIELD_TRUTH_RATIO:-0.06}"

NEXUS_THREAT_VECTOR_NAMES=(
  PACKET_INJECTION
  ARP_SPOOF
  DNS_POISON
  GATEWAY_SHIFT
  MITM_LISTENER
  RAW_SOCKET_INJECTION
  EGRESS_BEACON
  EGRESS_TMP_BINARY
  LISTENER_SURGE
  ICMP_REDIRECT
  RST_FLOOD
  CONN_HIJACK
  TLS_DOWNGRADE
  C2_CORRELATION
  SHUTDOWN_ATTACK
  RF_BURST
  WIFI_INTERFERENCE
  WIFI_THREAT
  FIELD_ANTENNA_ALERT
  AI_BEACON_PRECISION
  AI_LOLBIN_CHAIN
  AI_ROGUE_INFRA
  AI_EXFIL_SHAPE
  AI_AUTOSCAN
  AI_ML_C2_STACK
  AI_PHISH_FRAUD
  AI_DNS_TUNNEL
  LIE_DETECTED
  DECEPTION_INJECTION
  TRUTH_MANIPULATION
  HOSTILE_DECEPTION
)

nexus_threat_vector_init() {
  mkdir -p "$(dirname "$NEXUS_THREAT_VECTORS_DB")" 2>/dev/null || true
  [[ -f "$NEXUS_THREAT_VECTORS_DB" ]] || printf 'ts\tvector\tseverity\tdetail\n' >"$NEXUS_THREAT_VECTORS_DB"
}

nexus_threat_severity_rank() {
  case "${1:-low}" in
    critical) echo 4 ;;
    high) echo 3 ;;
    medium) echo 2 ;;
    *) echo 1 ;;
  esac
}

nexus_threat_record() {
  local vector="$1" severity="${2:-medium}" detail="$3"
  local ts
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)"
  nexus_threat_vector_init
  printf '%s\t%s\t%s\t%s\n' "$ts" "$vector" "$severity" "$detail" >>"$NEXUS_THREAT_VECTORS_DB"
  nexus_alert "threat-vectors" "THREAT_VECTOR_ALERT vector=${vector} severity=${severity} detail=${detail}"
  local trust_ip=""
  if declare -f nexus_firewall_parse_ip >/dev/null 2>&1; then
    trust_ip="$(nexus_firewall_parse_ip "$detail" "dst" 2>/dev/null)"
    [[ -z "$trust_ip" ]] && trust_ip="$(nexus_firewall_parse_ip "$detail" "ip" 2>/dev/null)"
  fi
  if [[ -n "$trust_ip" ]] && declare -f nexus_firewall_is_trusted >/dev/null 2>&1 \
    && nexus_firewall_is_trusted "$trust_ip" "both"; then
    nexus_log "INFO" "threat-vectors" "THREAT_TRUSTED_SKIP vector=${vector} ip=${trust_ip}"
    return 0
  fi
  if declare -f nexus_firewall_on_threat >/dev/null 2>&1; then
    nexus_threat_is_meta_vector "$vector" || nexus_firewall_on_threat "$vector" "$severity" "$detail"
  fi
  if declare -f nexus_paranoia_on_threat >/dev/null 2>&1; then
    nexus_paranoia_on_threat "$vector" "$severity" "$detail"
  fi
  if declare -f nexus_autosanitize_on_threat >/dev/null 2>&1; then
    if ! declare -f nexus_paranoia_enabled >/dev/null 2>&1 || ! nexus_paranoia_enabled; then
      nexus_autosanitize_on_threat "$vector" "$severity" "$detail"
    fi
  fi
}

nexus_threat_recent() {
  local limit="${1:-40}"
  tail -n "$((limit + 1))" "$NEXUS_THREAT_VECTORS_DB" 2>/dev/null | tail -n +2
}

nexus_threat_is_meta_vector() {
  local vector="$1"
  case "$vector" in
    C2_CORRELATION) return 0 ;;
  esac
  if declare -f nexus_paranoia_is_meta_vector >/dev/null 2>&1; then
    nexus_paranoia_is_meta_vector "$vector" && return 0
  fi
  return 1
}

nexus_threat_correlation_score() {
  local recent count=0 score=0 line vector sev w
  recent="$(nexus_threat_recent 80)"
  while IFS=$'\t' read -r _ vector sev _; do
    [[ -n "$vector" ]] || continue
    nexus_threat_is_meta_vector "$vector" && continue
    w="$(nexus_threat_severity_rank "$sev")"
    score=$((score + w))
    count=$((count + 1))
  done <<<"$recent"
  [[ "$count" -ge 3 ]] && score=$((score + 2))
  echo "$score"
}

nexus_threat_truth_signal() {
  local score max=100
  score="$(nexus_threat_correlation_score)"
  awk -v s="$score" -v m="$max" -v t="$NEXUS_FIELD_TRUTH_RATIO" 'BEGIN {
    sig = (s / 12.0) * m * t
    if (sig > m) sig = m
    printf "%.1f", sig
  }'
}