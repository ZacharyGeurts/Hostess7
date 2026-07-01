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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/adblock-loader.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Fair Ad Guardian — non-intrusive blocking; fair to advertisers and users.

NEXUS_ADBLOCK_DIR="${NEXUS_ADBLOCK_DIR:-${NEXUS_STATE_DIR}/adblock}"
NEXUS_ADBLOCK_DOMAINS="${NEXUS_ADBLOCK_DOMAINS:-${NEXUS_ADBLOCK_DIR}/domains.txt}"
NEXUS_ADBLOCK_BLOCKLIST="${NEXUS_ADBLOCK_BLOCKLIST:-${NEXUS_ADBLOCK_DIR}/domains-block.txt}"
NEXUS_ADBLOCK_STATE="${NEXUS_ADBLOCK_STATE:-${NEXUS_ADBLOCK_DIR}/state.json}"
NEXUS_ADBLOCK_GUARDIAN_JSON="${NEXUS_ADBLOCK_GUARDIAN_JSON:-${NEXUS_STATE_DIR}/adblock-guardian.json}"

NEXUS_ADBLOCK_LISTS=(
  "easylist|https://easylist.to/easylist/easylist.txt|EasyList"
  "easyprivacy|https://easylist.to/easylist/easyprivacy.txt|EasyPrivacy"
  "fanboy-annoyance|https://easylist.to/easylist/fanboy-annoyance.txt|Fanboy Annoyance"
)

nexus_adblock_init() {
  mkdir -p "$NEXUS_ADBLOCK_DIR" 2>/dev/null || true
  [[ -f "$NEXUS_ADBLOCK_DOMAINS" ]] || touch "$NEXUS_ADBLOCK_DOMAINS"
  chmod 640 "$NEXUS_ADBLOCK_DOMAINS" 2>/dev/null || true
}

nexus_adblock_get_policy() {
  local pol
  pol="$(nexus_settings_get NEXUS_ADBLOCK_POLICY 2>/dev/null)"
  [[ -n "$pol" ]] || pol="${NEXUS_ADBLOCK_POLICY:-annoyance}"
  case "$pol" in
    annoyance|fair|strict) printf '%s' "$pol" ;;
    *) printf 'annoyance' ;;
  esac
}

nexus_adblock_guardian_scan() {
  command -v pythong >/dev/null 2>&1 || return 0
  local script="${NEXUS_INSTALL_ROOT}/lib/fair-ad-guardian.py"
  [[ -f "$script" ]] || return 0
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$script" scan >/dev/null 2>&1 || true
}

nexus_adblock_build_blocklist() {
  command -v pythong >/dev/null 2>&1 || return 0
  local script="${NEXUS_INSTALL_ROOT}/lib/fair-ad-guardian.py"
  [[ -f "$script" ]] || return 0
  local pol
  pol="$(nexus_adblock_get_policy)"
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$script" blocklist "$pol" >/dev/null 2>&1 || true
}

nexus_adblock_fetch_list() {
  local id="$1" url="$2" name="${3:-$id}" dest tmp
  nexus_adblock_init
  dest="${NEXUS_ADBLOCK_DIR}/${id}.txt"
  tmp="${dest}.tmp"
  curl -fsSL --connect-timeout 20 --max-time 120 "$url" -o "$tmp" 2>/dev/null || {
    nexus_log "WARN" "adblock-loader" "FETCH_FAIL list=${id}"
    rm -f "$tmp"
    return 1
  }
  mv -f "$tmp" "$dest"
  grep -oE '^\|\|[^[:space:]/]+\^' "$dest" 2>/dev/null \
    | sed 's/^||//;s/\^$//' \
    | grep -E '^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$' \
    | sort -u >>"${NEXUS_ADBLOCK_DOMAINS}.new" 2>/dev/null || true
  sort -u "${NEXUS_ADBLOCK_DOMAINS}" "${NEXUS_ADBLOCK_DOMAINS}.new" 2>/dev/null \
    >"${NEXUS_ADBLOCK_DOMAINS}.merged" && mv -f "${NEXUS_ADBLOCK_DOMAINS}.merged" "$NEXUS_ADBLOCK_DOMAINS"
  rm -f "${NEXUS_ADBLOCK_DOMAINS}.new"
  nexus_log "INFO" "adblock-loader" "LOADED list=${name} domains_total=$(wc -l <"$NEXUS_ADBLOCK_DOMAINS" | tr -d ' ')"
  return 0
}

nexus_adblock_load_preset() {
  local preset="$1" id url name
  case "$preset" in
    easylist) nexus_adblock_fetch_list "easylist" "https://easylist.to/easylist/easylist.txt" "EasyList" ;;
    easyprivacy) nexus_adblock_fetch_list "easyprivacy" "https://easylist.to/easylist/easyprivacy.txt" "EasyPrivacy" ;;
    fanboy|annoyance) nexus_adblock_fetch_list "fanboy-annoyance" "https://easylist.to/easylist/fanboy-annoyance.txt" "Fanboy Annoyance" ;;
    *)
      for entry in "${NEXUS_ADBLOCK_LISTS[@]}"; do
        IFS='|' read -r id url name <<<"$entry"
        [[ "$id" == "$preset" ]] && { nexus_adblock_fetch_list "$id" "$url" "$name"; return $?; }
      done
      return 1
      ;;
  esac
}

nexus_adblock_load_url() {
  local url="$1" id
  [[ -n "$url" ]] || return 1
  id="custom-$(printf '%s' "$url" | md5sum 2>/dev/null | cut -c1-8)"
  nexus_adblock_fetch_list "$id" "$url" "Custom"
}

nexus_adblock_apply() {
  [[ "$(nexus_settings_get NEXUS_ADBLOCK 2>/dev/null || echo "${NEXUS_ADBLOCK:-0}")" == "1" ]] || return 0
  nexus_adblock_init
  declare -f nexus_firewall_available >/dev/null 2>&1 || return 0
  nexus_firewall_available || return 0

  nexus_adblock_guardian_scan
  nexus_adblock_build_blocklist

  local list_file="$NEXUS_ADBLOCK_BLOCKLIST" pol domain ip count=0 max
  pol="$(nexus_adblock_get_policy)"
  max="${NEXUS_ADBLOCK_RESOLVE_MAX:-400}"
  [[ "$pol" == "strict" && -s "$NEXUS_ADBLOCK_DOMAINS" ]] && list_file="$NEXUS_ADBLOCK_DOMAINS"
  [[ -s "$list_file" ]] || list_file="$NEXUS_ADBLOCK_BLOCKLIST"
  [[ -s "$list_file" ]] || {
    nexus_log "WARN" "adblock-loader" "APPLY_SKIP no blocklist policy=${pol}"
    return 0
  }

  while IFS= read -r domain; do
    [[ -n "$domain" ]] || continue
    [[ "$count" -ge "$max" ]] && break
    ip="$(getent ahostsv4 "$domain" 2>/dev/null | awk '{print $1; exit}')"
    [[ -n "$ip" ]] || continue
    if declare -f nexus_firewall_is_sacred_ip >/dev/null 2>&1 && nexus_firewall_is_sacred_ip "$ip"; then
      continue
    fi
    if declare -f nexus_firewall_is_trusted >/dev/null 2>&1 && nexus_firewall_is_trusted "$ip" "out"; then
      continue
    fi
    nft add element inet "${NEXUS_FIREWALL_TABLE}" block_out \
      "{ ${ip} timeout ${NEXUS_ADBLOCK_BLOCK_DURATION:-3600}s }" 2>/dev/null || true
    count=$((count + 1))
  done <"$list_file"

  local domain_count
  domain_count="$(wc -l <"$list_file" 2>/dev/null | tr -d ' ')"
  printf '{"domains":%s,"ips_blocked":%s,"policy":"%s","updated":"%s","mode":"fair_guardian"}\n' \
    "${domain_count:-0}" "$count" "$pol" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >"$NEXUS_ADBLOCK_STATE"
  nexus_log "INFO" "adblock-loader" "APPLY policy=${pol} ips=${count} domains=${domain_count}"
}

nexus_adblock_clear() {
  nexus_adblock_init
  : >"$NEXUS_ADBLOCK_BLOCKLIST" 2>/dev/null || true
  printf '{"domains":0,"ips_blocked":0,"policy":"off","updated":"%s","mode":"fair_guardian"}\n' \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >"$NEXUS_ADBLOCK_STATE"
  nexus_log "INFO" "adblock-loader" "CLEARED"
}

nexus_adblock_set_policy() {
  local pol="${1:-annoyance}"
  case "$pol" in
    annoyance|fair|strict) ;;
    *) return 1 ;;
  esac
  nexus_settings_set_str "NEXUS_ADBLOCK_POLICY" "$pol" || return 1
  if [[ "$(nexus_settings_get NEXUS_ADBLOCK 2>/dev/null || echo 0)" == "1" ]]; then
    nexus_adblock_apply
  fi
  return 0
}

nexus_adblock_site_policy() {
  local domain="${1:-}" policy="${2:-}" note="${3:-}"
  command -v pythong >/dev/null 2>&1 || return 1
  local script="${NEXUS_INSTALL_ROOT}/lib/fair-ad-guardian.py"
  [[ -f "$script" ]] || return 1
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$script" site-policy "$domain" "$policy" "$note" >/dev/null 2>&1
}

nexus_adblock_guardian_json() {
  command -v pythong >/dev/null 2>&1 || { printf '{}'; return 0; }
  local script="${NEXUS_INSTALL_ROOT}/lib/fair-ad-guardian.py"
  [[ -f "$script" ]] || { printf '{}'; return 0; }
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$script" status 2>/dev/null || printf '{}'
}

nexus_adblock_status_json() {
  nexus_adblock_init
  local domains=0 ips=0 enabled pol
  [[ -f "${NEXUS_ADBLOCK_BLOCKLIST}" ]] && domains="$(wc -l <"${NEXUS_ADBLOCK_BLOCKLIST}" 2>/dev/null | tr -d ' ')"
  [[ "${domains:-0}" -gt 0 ]] || domains="$(wc -l <"$NEXUS_ADBLOCK_DOMAINS" 2>/dev/null | tr -d ' ')"
  enabled="$(nexus_settings_get NEXUS_ADBLOCK 2>/dev/null || echo "${NEXUS_ADBLOCK:-0}")"
  pol="$(nexus_adblock_get_policy)"
  if [[ -f "$NEXUS_ADBLOCK_STATE" ]]; then
    ips="$(pythong -c 'import json; print(json.load(open("'"$NEXUS_ADBLOCK_STATE"'")).get("ips_blocked",0))' 2>/dev/null || echo 0)"
  fi
  printf '{"enabled":%s,"policy":"%s","domains":%s,"ips":%s,"mode":"fair_guardian"}' \
    "$enabled" "$pol" "${domains:-0}" "${ips:-0}"
}