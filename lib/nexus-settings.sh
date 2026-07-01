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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/nexus-settings.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS settings — panel-driven toggles via settings.override (no manual config editing).

NEXUS_SETTINGS_OVERRIDE="${NEXUS_SETTINGS_OVERRIDE:-${NEXUS_STATE_DIR}/settings.override}"

NEXUS_SETTINGS_KEYS=(
  NEXUS_AI_SECURE_CHANNEL
  QUEEN_AI_TELEMETRY_OK
  NEXUS_PARANOIA_BLOCK
  NEXUS_PARANOIA_MODE
  NEXUS_FIREWALL_AUTO_BLOCK
  NEXUS_AUTOSANITIZE
  NEXUS_ADBLOCK
  NEXUS_ADBLOCK_POLICY
  NEXUS_ADBLOCK_RESPECT_POLICY
  NEXUS_PANEL_AUTO_OPEN
  NEXUS_CONNECTION_GATEKEEPER
  NEXUS_PACKET_ORACLE
  NEXUS_SHADOW_WATCH
  NEXUS_ENTROPY_WATCH
  NEXUS_BEHAVIOR_WATCH
  NEXUS_PRIVACY_GUARD
  NEXUS_SHUTDOWN_GUARD
  NEXUS_HOSTESS7_CORROBORATE
  NEXUS_ATTACK_KIT_AUTO_CRUSH
  NEXUS_FIELD_AUTO_REKILL
  NEXUS_GATEKEEPER_STRICT_TRUST
  NEXUS_PACKET_PERMISSION
)

nexus_settings_init() {
  [[ -f "$NEXUS_SETTINGS_OVERRIDE" ]] || touch "$NEXUS_SETTINGS_OVERRIDE" 2>/dev/null || true
  chmod 640 "$NEXUS_SETTINGS_OVERRIDE" 2>/dev/null || true
  chown root:nexus "$NEXUS_SETTINGS_OVERRIDE" 2>/dev/null || true
}

nexus_settings_get() {
  local key="$1" val=""
  val="$(sed -n "s/^${key}=//p" "$NEXUS_SETTINGS_OVERRIDE" 2>/dev/null | tail -1)"
  if [[ -n "$val" ]]; then
    printf '%s' "$val"
    return 0
  fi
  val="${!key:-}"
  if [[ "$key" == "NEXUS_ADBLOCK_POLICY" ]]; then
    printf '%s' "${val:-annoyance}"
    return 0
  fi
  if [[ "$key" == "NEXUS_AI_SECURE_CHANNEL" || "$key" == "QUEEN_AI_TELEMETRY_OK" ]]; then
    printf '%s' "${val:-1}"
    return 0
  fi
  printf '%s' "${val:-0}"
}

nexus_settings_set_str() {
  local key="$1" val="$2" tmp
  nexus_settings_init
  case "$key" in
    NEXUS_ADBLOCK_POLICY)
      case "$val" in
        annoyance|fair|strict) ;;
        *) return 1 ;;
      esac
      ;;
    *) return 1 ;;
  esac
  tmp="${NEXUS_SETTINGS_OVERRIDE}.tmp"
  grep -v "^${key}=" "$NEXUS_SETTINGS_OVERRIDE" 2>/dev/null >"$tmp" || : >"$tmp"
  printf '%s=%s\n' "$key" "$val" >>"$tmp"
  mv -f "$tmp" "$NEXUS_SETTINGS_OVERRIDE"
  chmod 640 "$NEXUS_SETTINGS_OVERRIDE" 2>/dev/null || true
  nexus_log "INFO" "nexus-settings" "SET ${key}=${val}"
  return 0
}

nexus_settings_set() {
  local key="$1" val="$2" tmp
  nexus_settings_init
  case "$key" in
    NEXUS_AI_SECURE_CHANNEL|QUEEN_AI_TELEMETRY_OK|NEXUS_PARANOIA_BLOCK|NEXUS_PARANOIA_MODE|NEXUS_FIREWALL_AUTO_BLOCK|NEXUS_AUTOSANITIZE|NEXUS_ADBLOCK|NEXUS_ADBLOCK_RESPECT_POLICY|NEXUS_PANEL_AUTO_OPEN|NEXUS_CONNECTION_GATEKEEPER|NEXUS_PACKET_ORACLE|NEXUS_SHADOW_WATCH|NEXUS_ENTROPY_WATCH|NEXUS_BEHAVIOR_WATCH|NEXUS_PRIVACY_GUARD|NEXUS_SHUTDOWN_GUARD|NEXUS_HOSTESS7_CORROBORATE|NEXUS_ATTACK_KIT_AUTO_CRUSH|NEXUS_FIELD_AUTO_REKILL|NEXUS_GATEKEEPER_STRICT_TRUST|NEXUS_PACKET_PERMISSION) ;;
    *) return 1 ;;
  esac
  [[ "$val" == "1" || "$val" == "0" ]] || return 1
  tmp="${NEXUS_SETTINGS_OVERRIDE}.tmp"
  grep -v "^${key}=" "$NEXUS_SETTINGS_OVERRIDE" 2>/dev/null >"$tmp" || : >"$tmp"
  printf '%s=%s\n' "$key" "$val" >>"$tmp"
  mv -f "$tmp" "$NEXUS_SETTINGS_OVERRIDE"
  chmod 640 "$NEXUS_SETTINGS_OVERRIDE" 2>/dev/null || true

  case "$key" in
    NEXUS_PARANOIA_BLOCK)
      declare -f nexus_paranoia_set_block >/dev/null 2>&1 && nexus_paranoia_set_block "$val"
      ;;
    NEXUS_AUTOSANITIZE)
      declare -f nexus_autosanitize_set_enabled >/dev/null 2>&1 && nexus_autosanitize_set_enabled "$val"
      ;;
    NEXUS_ADBLOCK)
      if [[ "$val" == "1" ]]; then
        declare -f nexus_adblock_apply >/dev/null 2>&1 && nexus_adblock_apply || true
      else
        declare -f nexus_adblock_clear >/dev/null 2>&1 && nexus_adblock_clear || true
      fi
      ;;
  esac
  nexus_log "INFO" "nexus-settings" "SET ${key}=${val}"
  return 0
}

# Secure profile — watchers and auto-block ON when they harden the field.
nexus_settings_apply_consumer_defaults() {
  nexus_settings_init
  local kv key val
  for kv in \
    NEXUS_PARANOIA_BLOCK=1 \
    NEXUS_PARANOIA_MODE=1 \
    NEXUS_FIREWALL_AUTO_BLOCK=1 \
    NEXUS_AUTOSANITIZE=1 \
    NEXUS_ADBLOCK=1 \
    NEXUS_ADBLOCK_RESPECT_POLICY=1 \
    NEXUS_PANEL_AUTO_OPEN=1 \
    NEXUS_CONNECTION_GATEKEEPER=1 \
    NEXUS_PACKET_ORACLE=1 \
    NEXUS_SHADOW_WATCH=1 \
    NEXUS_ENTROPY_WATCH=1 \
    NEXUS_BEHAVIOR_WATCH=1 \
    NEXUS_PRIVACY_GUARD=1 \
    NEXUS_SHUTDOWN_GUARD=1 \
    NEXUS_HOSTESS7_CORROBORATE=1 \
    NEXUS_ATTACK_KIT_AUTO_CRUSH=1 \
    NEXUS_FIELD_AUTO_REKILL=1 \
    NEXUS_GATEKEEPER_STRICT_TRUST=1 \
    NEXUS_PACKET_PERMISSION=1
  do
    key="${kv%%=*}"
    val="${kv#*=}"
    nexus_settings_set "$key" "$val" || return 1
  done
  nexus_settings_set_str "NEXUS_ADBLOCK_POLICY" "annoyance" || return 1
  nexus_log "INFO" "nexus-settings" "SECURE_DEFAULTS applied (dusty midnight secure profile)"
  return 0
}

# EXTREME envelope — all watchers hardened; adblock stays relaxed (fair) for 4★/5★ hosts.
nexus_settings_apply_extreme_defaults() {
  nexus_settings_apply_consumer_defaults || return 1
  nexus_settings_set_str "NEXUS_ADBLOCK_POLICY" "fair" || return 1
  nexus_log "INFO" "nexus-settings" "EXTREME_DEFAULTS applied (watchers max, adblock fair/relaxed)"
  return 0
}

nexus_host_extreme_apply_if_eligible() {
  local tier_json level
  tier_json="$(pythong "${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}/lib/host-security-tier.py" json 2>/dev/null)" || return 0
  level="$(printf '%s' "$tier_json" | pythong -c 'import json,sys; d=json.load(sys.stdin); print(d.get("security_level",""))' 2>/dev/null)" || return 0
  if [[ "$level" == "extreme" ]]; then
    nexus_settings_apply_extreme_defaults
    pythong "${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}/lib/host-security-tier.py" publish >/dev/null 2>&1 || true
    return 0
  fi
  return 1
}

nexus_settings_json() {
  nexus_settings_init
  local key val first=1
  printf '{'
  for key in "${NEXUS_SETTINGS_KEYS[@]}"; do
    val="$(nexus_settings_get "$key")"
    if [[ "$key" == "NEXUS_AI_SECURE_CHANNEL" || "$key" == "QUEEN_AI_TELEMETRY_OK" ]]; then
      [[ -n "$val" ]] || val="1"
      [[ "$first" -eq 1 ]] || printf ','
      first=0
      printf '"%s":%s' "$key" "$val"
      continue
    fi
    if [[ "$key" == "NEXUS_ADBLOCK_POLICY" ]]; then
      [[ -n "$val" ]] || val="annoyance"
      [[ "$first" -eq 1 ]] || printf ','
      first=0
      printf '"%s":"%s"' "$key" "$val"
      continue
    fi
    [[ -n "$val" ]] || val="0"
    [[ "$first" -eq 1 ]] || printf ','
    first=0
    printf '"%s":%s' "$key" "$val"
  done
  if declare -f nexus_adblock_status_json >/dev/null 2>&1; then
    [[ "$first" -eq 1 ]] || printf ','
    first=0
    printf '"adblock":'
    nexus_adblock_status_json
  else
    [[ "$first" -eq 1 ]] || printf ','
    first=0
    printf '"adblock":{"enabled":0,"domains":0,"ips":0,"policy":"annoyance","mode":"fair_guardian"}'
  fi
  if declare -f nexus_adblock_guardian_json >/dev/null 2>&1; then
    [[ "$first" -eq 1 ]] || printf ','
    first=0
    printf '"adblock_guardian":'
    nexus_adblock_guardian_json
  fi
  local ai_py="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}/lib/nexus-ai-telemetry.py"
  if [[ -f "$ai_py" ]]; then
    [[ "$first" -eq 1 ]] || printf ','
    first=0
    printf '"ai_telemetry":'
    NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
      pythong "$ai_py" json 2>/dev/null | sed -n '1,999p' || printf '{"ai_telemetry_on":true,"data_release":false}'
  fi
  printf '}'
}

nexus_settings_apply_hostess7_armed_defaults() {
  nexus_settings_apply_extreme_defaults || nexus_settings_apply_consumer_defaults || return 1
  local wd="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}/lib/hostess7-weapons-defense.py"
  if [[ -f "$wd" ]]; then
    NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      NEXUS_HOSTESS7_FULL_CONTROL=1 NEXUS_HOSTESS7_SYSTEM_CONTROL=1 \
      pythong "$wd" turnover >/dev/null 2>&1 || true
  fi
  nexus_log "INFO" "nexus-settings" "Hostess 7 armed defaults — weapons and defenses turnover"
}

nexus_settings_apply_ammoos_defaults() {
  local engine="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}/lib/ammoos-theme-engine.py"
  local doctrine="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}/data/ammoos-themes-doctrine.json"
  local theme="nexus_c2"
  if [[ -f "$doctrine" ]]; then
    theme="$(pythong -c 'import json,sys; print(json.load(open(sys.argv[1])).get("default_ammoos_theme","nexus_c2"))' "$doctrine" 2>/dev/null || echo nexus_c2)"
  fi
  if [[ -f "$engine" ]]; then
    NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      pythong "$engine" apply <<<"{\"active_c2\":\"${theme}\"}" >/dev/null 2>&1 || true
  fi
  nexus_log "INFO" "nexus-settings" "ammoos theme defaults applied (${theme})"
}