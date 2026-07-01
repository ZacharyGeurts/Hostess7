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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/threat-panel.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Threat Panel — Internet + Threat side-by-side state (AMOURANTHRTX field corroboration).
# AMOURANTHRTX: GPL v3 or commercial (not MIT-free). NEXUS-Shield: MIT.

NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
# shellcheck source=/dev/null
[[ -f "${NEXUS_INSTALL_ROOT}/lib/threat-autosanitize.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/threat-autosanitize.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/paranoia-mode.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/paranoia-mode.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/firewall-trust.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/firewall-trust.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/nexus-settings.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/nexus-settings.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/adblock-loader.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/adblock-loader.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/shutdown-guard.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/shutdown-guard.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/vector-scour.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/vector-scour.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/pest-arsenal.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/pest-arsenal.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/angel-dossier.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/angel-dossier.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/human-dossier.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/human-dossier.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/field-us-intel.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/field-us-intel.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/host-attack.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/host-attack.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/planetary-observer.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/planetary-observer.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/field-attack-kit.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/field-attack-kit.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/honorability.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/honorability.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/panel-i18n.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/panel-i18n.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/field-rf-sentinel.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/field-rf-sentinel.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/police-agency.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/police-agency.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/field-command.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/field-command.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/gov-intel.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/gov-intel.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/program-tags.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/program-tags.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/nexus-plugins.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/nexus-plugins.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/terror-spiderweb.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/terror-spiderweb.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/precision-field.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/precision-field.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/hostess7-field.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/hostess7-field.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/hostess7-operator.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/hostess7-operator.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/human-registry.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/human-registry.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/field-antenna-guard.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/field-antenna-guard.sh"
[[ "${NEXUS_AUDIO_TRAIN:-0}" == "1" && -f "${NEXUS_INSTALL_ROOT}/lib/audio-train.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/audio-train.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/home-protector.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/home-protector.sh"
[[ "${NEXUS_SIGNALS_FIELD:-0}" == "1" && -f "${NEXUS_INSTALL_ROOT}/lib/signals-field.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/signals-field.sh"

[[ "${NEXUS_FIELD_RADIO:-0}" == "1" && -f "${NEXUS_INSTALL_ROOT}/lib/field-radio-catcher.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/field-radio-catcher.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/field-dns.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/field-dns.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/field-outside-talk.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/field-outside-talk.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/field-drive-system.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/field-drive-system.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/dns-admin-portal.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/dns-admin-portal.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/field-gui-publish.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/field-gui-publish.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/field-brain-sync.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/field-brain-sync.sh"

NEXUS_THREAT_PANEL_JSON="${NEXUS_THREAT_PANEL_JSON:-${NEXUS_STATE_DIR}/threat-panel.json}"

nexus_threat_panel_refresh_globe() {
  if declare -f nexus_host_attack_publish_deep >/dev/null 2>&1; then
    nexus_host_attack_publish_deep
  elif declare -f nexus_host_attack_publish >/dev/null 2>&1; then
    nexus_host_attack_publish
  fi
  if declare -f nexus_human_dossier_sync >/dev/null 2>&1; then
    nexus_human_dossier_sync
  fi
}
NEXUS_THREAT_PANEL_PORT="${NEXUS_THREAT_PANEL_PORT:-9477}"

nexus_threat_panel_publish() {
  [[ "${NEXUS_THREAT_PANEL:-1}" == "1" ]] || return 0
  local lock="${NEXUS_STATE_DIR}/threat-panel.publish.lock"
  exec 9>"$lock" 2>/dev/null || return 0
  flock -w 5 9 2>/dev/null || return 0
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/ironclad-immediate.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/ironclad-immediate.sh"
    nexus_ironclad_immediate_publish
  fi
  if [[ "${NEXUS_PANEL_PUBLISH_FAST:-}" != "1" ]]; then
    if declare -f nexus_field_brain_sync >/dev/null 2>&1; then
      nexus_field_brain_sync
    fi
    if declare -f nexus_field_gui_publish_all >/dev/null 2>&1; then
      nexus_field_gui_publish_all
    fi
    if declare -f nexus_field_rf_cycle >/dev/null 2>&1; then
      nexus_field_rf_cycle
    fi
    # Spiderweb + precision: operator-triggered only (NEXUS_TERROR_SPIDERWEB=1 to auto-publish).
    if [[ "${NEXUS_TERROR_SPIDERWEB:-0}" == "1" ]] && declare -f nexus_terror_spiderweb_publish >/dev/null 2>&1; then
      nexus_terror_spiderweb_publish
    fi
    if [[ "${NEXUS_PRECISION_FIELD:-0}" == "1" ]] && declare -f nexus_precision_field_publish >/dev/null 2>&1; then
      nexus_precision_field_publish
    fi
    if declare -f nexus_hostess7_autonomous_cycle >/dev/null 2>&1; then
      nexus_hostess7_autonomous_cycle
    fi
    if declare -f nexus_field_attack_rekill_cycle >/dev/null 2>&1; then
      nexus_field_attack_rekill_cycle
    fi
    if declare -f nexus_audio_train_publish >/dev/null 2>&1; then
      nexus_audio_train_publish
    fi
    if declare -f nexus_home_protector_publish >/dev/null 2>&1; then
      nexus_home_protector_publish
    fi
    if declare -f nexus_field_radio_publish >/dev/null 2>&1; then
      nexus_field_radio_publish
    fi
    if declare -f nexus_signals_field_publish >/dev/null 2>&1; then
      nexus_signals_field_publish
    fi
    if declare -f nexus_field_dns_publish >/dev/null 2>&1; then
      nexus_field_dns_publish
    fi
    if declare -f nexus_field_outside_talk_publish >/dev/null 2>&1; then
      nexus_field_outside_talk_publish
    fi
    if declare -f nexus_field_drive_publish >/dev/null 2>&1; then
      nexus_field_drive_publish
    fi
    if declare -f nexus_dns_admin_publish >/dev/null 2>&1; then
      nexus_dns_admin_publish
    fi
  fi
  local ts mode conn arp egress listeners threats corr signal dns
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)"
  mode="$(nexus_vigil_get_mode 2>/dev/null || echo calm)"
  conn="$(nexus_packet_snapshot_connections 2>/dev/null | head -n 80)"
  arp="$(nexus_packet_snapshot_arp 2>/dev/null | head -n 40)"
  egress="$(grep -cE 'ESTAB|ESTABLISHED' <<<"$conn" 2>/dev/null)"; egress="${egress:-0}"
  listeners="$(grep -c LISTEN <<<"$conn" 2>/dev/null)"; listeners="${listeners:-0}"
  threats="$(nexus_threat_recent 40)"
  corr="$(nexus_threat_correlation_score 2>/dev/null || echo 0)"
  signal="$(nexus_threat_truth_signal 2>/dev/null || echo 0)"
  dns="$(nexus_packet_resolv_hash 2>/dev/null || echo none)"

  {
    printf '{'
    printf '"updated":"%s",' "$ts"
    printf '"vigil_mode":"%s",' "$mode"
    printf '"noise_ratio":%s,' "${NEXUS_FIELD_NOISE_RATIO:-0.94}"
    printf '"truth_ratio":%s,' "${NEXUS_FIELD_TRUTH_RATIO:-0.06}"
    printf '"truth_signal":%s,' "$signal"
    printf '"correlation_score":%s,' "$corr"
    if declare -f nexus_firewall_status >/dev/null 2>&1; then
      local fw_state fw_blocks
      fw_state="$(nexus_firewall_status 2>/dev/null | awk -F= '/^firewall=/ {print $2}')"
      fw_blocks="$(nexus_firewall_status 2>/dev/null | awk -F= '/^blocks=/ {print $2}')"
      printf '"firewall":"%s",' "${fw_state:-checking}"
      printf '"firewall_blocks":%s,' "${fw_blocks:-0}"
    fi
    printf '"internet":{'
    printf '"egress_count":%s,' "$egress"
    printf '"listener_count":%s,' "$listeners"
    printf '"dns_hash":"%s",' "$dns"
    printf '"connections":['
    local first=1 line esc
    while IFS= read -r line; do
      [[ -n "$line" ]] || continue
      esc="$(printf '%s' "$line" | sed 's/\\/\\\\/g; s/"/\\"/g')"
      [[ "$first" -eq 1 ]] || printf ','
      first=0
      printf '"%s"' "$esc"
    done <<<"$conn"
    printf '],'
    printf '"arp":['
    first=1
    while IFS= read -r line; do
      [[ -n "$line" ]] || continue
      esc="$(printf '%s' "$line" | sed 's/\\/\\\\/g; s/"/\\"/g')"
      [[ "$first" -eq 1 ]] || printf ','
      first=0
      printf '"%s"' "$esc"
    done <<<"$arp"
    printf ']'
    printf '},'
    printf '"blocked":'
    if declare -f nexus_firewall_blocks_json >/dev/null 2>&1; then
      nexus_firewall_blocks_json
    else
      printf '[]'
    fi
    printf ',"lockdown_first":'
    if [[ -f "${NEXUS_STATE_DIR}/lockdown-first.done" ]]; then
      printf 'true'
    else
      printf 'false'
    fi
    printf ',"trusted":'
    if declare -f nexus_firewall_trust_json >/dev/null 2>&1; then
      nexus_firewall_trust_json
    else
      printf '[]'
    fi
    printf ',"trust_count":'
    if declare -f nexus_firewall_trust_count >/dev/null 2>&1; then
      nexus_firewall_trust_count
    else
      printf '0'
    fi
    printf ',"threats":['
    first=1
    local t_vector t_sev t_detail t_ts
    while IFS=$'\t' read -r t_ts t_vector t_sev t_detail; do
      [[ -n "$t_vector" ]] || continue
      esc="$(printf '%s' "$t_detail" | sed 's/\\/\\\\/g; s/"/\\"/g')"
      [[ "$first" -eq 1 ]] || printf ','
      first=0
      printf '{"ts":"%s","vector":"%s","severity":"%s","detail":"%s"}' "$t_ts" "$t_vector" "$t_sev" "$esc"
    done <<<"$threats"
    printf '],'
    printf '"vectors":[ '
    local v first_v=1
    for v in "${NEXUS_THREAT_VECTOR_NAMES[@]}"; do
      [[ "$first_v" -eq 1 ]] || printf ','
      first_v=0
      printf '"%s"' "$v"
    done
    printf ' ],'
    printf '"autosanitize":{'
    if declare -f nexus_autosanitize_is_on >/dev/null 2>&1 && nexus_autosanitize_is_on 2>/dev/null; then
      printf '"enabled":true,'
    else
      printf '"enabled":false,'
    fi
    printf '"actions":'
    if declare -f nexus_autosanitize_json_actions >/dev/null 2>&1; then
      nexus_autosanitize_json_actions 25
    else
      printf '[]'
    fi
    printf '},'
    printf '"paranoia":'
    if declare -f nexus_paranoia_panel_json >/dev/null 2>&1; then
      nexus_paranoia_panel_json
    else
      printf '{"enabled":false,"block":false,"incidents":[]}'
    fi
    printf ',"settings":'
    if declare -f nexus_settings_json >/dev/null 2>&1; then
      nexus_settings_json
    else
      printf '{}'
    fi
    printf ',"packet_field":'
    if [[ -s "${NEXUS_STATE_DIR}/packet-field.json" ]]; then
      pythong -c "import json,sys; json.dump(json.load(open(sys.argv[1])), sys.stdout)" \
        "${NEXUS_STATE_DIR}/packet-field.json" 2>/dev/null || printf '{}'
    else
      printf '{}'
    fi
    printf ',"h7_library":'
    if [[ -f "${NEXUS_INSTALL_ROOT}/lib/h7-library-bridge.py" ]]; then
      NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
        HOSTESS7_ROOT="${HOSTESS7_ROOT:-${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}/Hostess7}" \
        HOSTESS7_TEAM_FIELD="${HOSTESS7_TEAM_FIELD:-/media/default/HOSTESS7_TEAM/fieldstorage}" \
        pythong "${NEXUS_INSTALL_ROOT}/lib/h7-library-bridge.py" build 2>/dev/null \
        || printf '{"books":[],"shelves":[]}'
    else
      printf '{"books":[],"shelves":[]}'
    fi
    printf ',"gatekeeper":'
    if [[ -s "${NEXUS_STATE_DIR}/connection-intent.json" ]]; then
      pythong -c "import json,sys; json.dump(json.load(open(sys.argv[1])), sys.stdout)" \
        "${NEXUS_STATE_DIR}/connection-intent.json" 2>/dev/null \
        || printf '{"connections":[],"harm_candidates":0}'
    else
      printf '{"connections":[],"harm_candidates":0,"why_no_auto_block":"Gatekeeper warming up…"}'
    fi
    printf ',"shutdown":'
    if declare -f nexus_shutdown_status_json >/dev/null 2>&1; then
      nexus_shutdown_status_json
    else
      printf '{"killed":false,"status":"idle","incidents":[]}'
    fi
    printf ',"vector_intel":'
    if declare -f nexus_vector_intel_json >/dev/null 2>&1; then
      nexus_vector_intel_json
    else
      printf '{"active_count":0,"pest_count":0,"active_vectors":[],"pests":[],"never_unknown":true}'
    fi
    printf ',"pest_actions":'
    if declare -f nexus_pest_actions_json >/dev/null 2>&1; then
      nexus_pest_actions_json 15
    else
      printf '[]'
    fi
    printf ',"angel_dossiers":'
    if declare -f nexus_angel_dossiers_json >/dev/null 2>&1; then
      nexus_angel_dossiers_json
    else
      printf '{"dossier_count":0,"dossiers":[],"motto":"Let'\''s Be Angels"}'
    fi
    printf ',"angel_research":'
    if declare -f nexus_angel_research_json >/dev/null 2>&1; then
      nexus_angel_research_json
    else
      printf '{"tables":{"mac_vendors":[],"exploit_cve_map":[]}}'
    fi
    printf ',"us_field":'
    if declare -f nexus_us_field_json >/dev/null 2>&1; then
      nexus_us_field_json
    else
      printf '{"page":1,"title":"US","observations":["US field intel module not loaded."]}'
    fi
    printf ',"human_registry":'
    if declare -f nexus_human_registry_json >/dev/null 2>&1; then
      nexus_human_registry_json
    else
      printf '{"schema":"human-registry/v1","stats":{"total":0},"table":[],"humans":{}}'
    fi
    printf ',"audio_train":'
    if declare -f nexus_audio_train_json >/dev/null 2>&1; then
      nexus_audio_train_json
    else
      printf '{"schema":"audio-train/v1","hostess_version":"7","stats":{"sources":0},"sources":{},"table":[]}'
    fi
    printf ',"home_protector":'
    if declare -f nexus_home_protector_json >/dev/null 2>&1; then
      nexus_home_protector_json
    else
      printf '{"schema":"home-protector/v1","stats":{"total":0},"entities":[],"table":[]}'
    fi
    printf ',"human_dossier":'
    if declare -f nexus_human_dossier_json >/dev/null 2>&1; then
      nexus_human_dossier_json
    else
      printf '{"dossier_version":"7.0","ip_count":0,"ips":[],"analyst":"Grok Heavy"}'
    fi
    printf ',"signals_field":'
    if declare -f nexus_signals_field_json >/dev/null 2>&1; then
      nexus_signals_field_json
    else
      printf '{"schema":"signals-field/v1","stats":{"antenna_fields":0},"antennas":[],"pulse_channels":[]}'
    fi
    printf ',"field_antenna":{"schema":"field-antenna/v1","removed":true,"reason":"field_antenna_removed"}'
    printf ',"field_radio":'
    if declare -f nexus_field_radio_json >/dev/null 2>&1; then
      nexus_field_radio_json
    else
      printf '{"schema":"field-radio-catcher/v1","station_menu":[],"illegal_frequencies":[],"stats":{"menu_count":0}}'
    fi
    printf ',"field_dns":'
    if declare -f nexus_field_dns_json >/dev/null 2>&1; then
      nexus_field_dns_json
    else
      printf '{"schema":"field-dns/v2","running":false,"rfc_matrix":[],"legal_framework":[],"zones":[]}'
    fi
    printf ',"field_outside_talk":'
    if declare -f nexus_field_outside_talk_json >/dev/null 2>&1; then
      nexus_field_outside_talk_json
    else
      printf '{"schema":"field-outside-talk/v1","tools":[],"firewall":{"active":false},"recent_sessions":[]}'
    fi
    printf ',"field_drive":'
    if declare -f nexus_field_drive_json >/dev/null 2>&1; then
      nexus_field_drive_json
    else
      printf '{"schema":"field-drive-system/v1","drive_mounted":false,"whole_system_on_drive":false,"drives":[],"gui_on_drive":false,"panel_url":"/field"}'
    fi
    printf ',"dns_admin_portal":'
    if declare -f nexus_dns_admin_status_json >/dev/null 2>&1; then
      nexus_dns_admin_status_json
    else
      printf '{"schema":"dns-admin-portal/v1","ports":[7,77,777],"policy":"information_only"}'
    fi
    printf ',"adblock_guardian":'
    if declare -f nexus_adblock_guardian_json >/dev/null 2>&1; then
      nexus_adblock_guardian_json
    else
      printf '{}'
    fi
    printf ',"host_attacks":'
    if declare -f nexus_host_attacks_panel_json >/dev/null 2>&1; then
      nexus_host_attacks_panel_json
    elif declare -f nexus_host_attacks_json >/dev/null 2>&1; then
      nexus_host_attacks_json
    else
      printf '{"points":[],"stats":{"total":0,"hot":0,"warm":0,"cool":0}}'
    fi
    printf ',"planetary_observer":'
    if declare -f nexus_planetary_observer_json >/dev/null 2>&1; then
      nexus_planetary_observer_json
    else
      printf '{"schema":"planetary-observer/v1","globe":{"total_targets":0,"strike_certain":0},"wire":{"harm_candidates":0},"proactive_enabled":false}'
    fi
    printf ',"attack_kit":'
    if declare -f nexus_field_attack_json >/dev/null 2>&1; then
      nexus_field_attack_json
    else
      printf '{"disabled_count":0,"hosts":[]}'
    fi
    printf ',"browser_awareness":'
    if declare -f nexus_honorability_json >/dev/null 2>&1; then
      nexus_honorability_json
    else
      printf '{"active_sites":[],"honorability":{"entries":[]}}'
    fi
    printf ',"operator_location":'
    if declare -f nexus_operator_location_json >/dev/null 2>&1; then
      nexus_operator_location_json
    else
      printf '{"lat":null,"lon":null,"source":"unset"}'
    fi
    printf ',"panel_language":'
    if declare -f nexus_panel_language_json >/dev/null 2>&1; then
      nexus_panel_language_json
    else
      printf '{"schema":"panel-language/v1","active":{"code":"en-US","source":"default"},"languages":[],"messages":{}}'
    fi
    printf ',"field_rf":'
    if declare -f nexus_field_rf_json >/dev/null 2>&1; then
      nexus_field_rf_json
    else
      printf '{"antenna":{"mode":"unavailable"},"bursts":[],"shield":{"enabled":true}}'
    fi
    printf ',"police_agency":'
    if declare -f nexus_police_agency_json >/dev/null 2>&1; then
      nexus_police_agency_json
    else
      printf '{"agencies":[],"selected":null}'
    fi
    printf ',"field_command":'
    if declare -f nexus_field_command_json >/dev/null 2>&1; then
      nexus_field_command_json
    else
      printf '{"good_guy":{"count":0},"bad_guy":{"count":0},"pulse":{}}'
    fi
    printf ',"gov_intel":'
    if declare -f nexus_gov_intel_json >/dev/null 2>&1; then
      nexus_gov_intel_json
    else
      printf '{"merge_only":true,"record_count":0}'
    fi
    printf ',"program_tags":'
    if declare -f nexus_program_tags_json >/dev/null 2>&1; then
      nexus_program_tags_json
    else
      printf '{"merge_only":true,"program_count":0}'
    fi
    printf ',"terror_spiderweb":'
    if declare -f nexus_terror_spiderweb_json >/dev/null 2>&1; then
      nexus_terror_spiderweb_json
    else
      printf '{"nodes":[],"edges":[],"focus":{}}'
    fi
    printf ',"precision_field":'
    if declare -f nexus_precision_field_json >/dev/null 2>&1; then
      nexus_precision_field_json
    else
      printf '{"entities":[],"edges":[],"stats":{}}'
    fi
    printf ',"field_hardware":'
    if declare -f nexus_field_hardware_json >/dev/null 2>&1; then
      nexus_field_hardware_json
    else
      printf '{"schema":"field-hardware-probe/v1"}'
    fi
    printf ',"field_hazard_onset":'
    if declare -f nexus_field_hazard_onset_json >/dev/null 2>&1; then
      nexus_field_hazard_onset_json
    else
      printf '{"schema":"field-hazard-onset-panel/v1"}'
    fi
    printf ',"lethal_enforcement":'
    if declare -f nexus_lethal_enforcement_json >/dev/null 2>&1; then
      nexus_lethal_enforcement_json
    else
      printf '{"schema":"lethal-enforcement-panel/v1"}'
    fi
    printf ',"hostess7_lethal_insight":'
    if declare -f nexus_hostess7_lethal_insight_json >/dev/null 2>&1; then
      nexus_hostess7_lethal_insight_json
    else
      printf '{"schema":"hostess7-lethal-insight-panel/v1"}'
    fi
    printf ',"field_brain":'
    if [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-brain-panel.py" ]]; then
      NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
        pythong "${NEXUS_INSTALL_ROOT}/lib/field-brain-panel.py" json 2>/dev/null \
        || printf '{"schema":"field-brain/v1","ok":false}'
    else
      printf '{"schema":"field-brain/v1","ok":false}'
    fi
    printf ',"field_antenna_catch":{"schema":"field-antenna-catch/v1","removed":true}'
    printf ',"field":true'
    printf ',"panel_ready":true'
    printf ',"version":"%s"' "${NEXUS_VERSION}"
    printf '}\n'
  } >"${NEXUS_THREAT_PANEL_JSON}.tmp" 2>/dev/null \
    && pythong -c "import json,sys; json.load(open(sys.argv[1], encoding='utf-8'))" "${NEXUS_THREAT_PANEL_JSON}.tmp" 2>/dev/null \
    && mv -f "${NEXUS_THREAT_PANEL_JSON}.tmp" "$NEXUS_THREAT_PANEL_JSON"
  chmod 640 "$NEXUS_THREAT_PANEL_JSON" 2>/dev/null || true
  chown root:nexus "$NEXUS_THREAT_PANEL_JSON" 2>/dev/null || true
  if declare -f nexus_plugins_merge_panel >/dev/null 2>&1; then
    nexus_plugins_merge_panel
  fi
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-panel-parallel.py" ]]; then
    NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
      pythong "${NEXUS_INSTALL_ROOT}/lib/field-panel-parallel.py" publish >/dev/null 2>&1 || true
  fi
  flock -u 9 2>/dev/null || true
}

nexus_threat_panel_stop_stale() {
  # Never kill panel.pid here — start_module writes it async; killing races with our own subshell.
  pkill -9 -f 'threat-panel-http.py' 2>/dev/null || true
  command -v fuser >/dev/null 2>&1 && fuser -k "${NEXUS_THREAT_PANEL_PORT:-9477}/tcp" 2>/dev/null || true
  sleep 1
}

nexus_threat_panel_serve_loop() {
  [[ "${NEXUS_THREAT_PANEL:-1}" == "1" ]] || return 0
  command -v pythong >/dev/null 2>&1 || {
    nexus_log "WARN" "threat-panel" "pythong missing; panel JSON only at ${NEXUS_THREAT_PANEL_JSON}"
    return 0
  }
  nexus_threat_panel_stop_stale
  printf '%s\n' "$$" >"${NEXUS_STATE_DIR}/panel.pid"
  # shellcheck source=/dev/null
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/znetwork-field.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/znetwork-field.sh"
  nexus_znetwork_publish 2>/dev/null || true
  local panel_dir="${NEXUS_INSTALL_ROOT}/panel"
  local port="$NEXUS_THREAT_PANEL_PORT"
  export NEXUS_STATE_DIR
  while true; do
    NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" NEXUS_STATE_DIR="$NEXUS_STATE_DIR" \
      pythong "${NEXUS_INSTALL_ROOT}/lib/threat-panel-http.py" \
      "$port" "$panel_dir" "$NEXUS_THREAT_PANEL_JSON" \
      >>"${NEXUS_STATE_DIR}/panel-http.log" 2>&1
    printf '%s\n' "$$" >"${NEXUS_STATE_DIR}/panel.pid"
    sleep 5
  done
}