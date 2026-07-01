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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/nexus-daemon.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS genius-layer daemon — event-driven, ultra-stealth, self-verified.
set -euo pipefail

NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"

# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/nexus-common.sh"
nexus_init_runtime_paths
nexus_load_config
# shellcheck source=/dev/null
[[ -f "${NEXUS_INSTALL_ROOT}/lib/nexus-boot-impl.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/nexus-boot-impl.sh"
declare -f nexus_boot_impl_run >/dev/null 2>&1 && nexus_boot_impl_run || true
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/self-defense.sh"
nexus_verify_integrity || exit 1
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/ultra-stealth.sh"
nexus_apply_cgroup_self
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/eternal-vigil.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/predictive-guard.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/shadow-reality.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/entropy-oracle.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/behavior-symphony.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/privacy-guard.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/device-whitelist.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/network-lockdown.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/seal-vault.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/tamper-guard.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/hostess7-bridge.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/hostess7-operator.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/kilroy-core.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/firewall-sentinel.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/firewall-trust.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/self-access.sh"
nexus_firewall_trust_init
nexus_firewall_trust_sync_from_memory
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/field-attack-kit.sh"
nexus_field_attack_sync_from_memory
nexus_field_attack_apply_registry
[[ -f "${NEXUS_INSTALL_ROOT}/lib/field-war-hardening.sh" ]] && {
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/field-war-hardening.sh"
  nexus_field_war_harden || true
}
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/threat-vectors.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/threat-autosanitize.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/paranoia-mode.sh"
nexus_paranoia_init
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/shutdown-guard.sh"
nexus_shutdown_init
nexus_shutdown_install_traps
nexus_shutdown_startup_check
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/vector-scour.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/angel-dossier.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/human-registry.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/human-registry.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/field-antenna-guard.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/field-antenna-guard.sh"
[[ "${NEXUS_AUDIO_TRAIN:-0}" == "1" && -f "${NEXUS_INSTALL_ROOT}/lib/audio-train.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/audio-train.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/home-protector.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/home-protector.sh"
[[ "${NEXUS_SIGNALS_FIELD:-0}" == "1" && -f "${NEXUS_INSTALL_ROOT}/lib/signals-field.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/signals-field.sh"

[[ -f "${NEXUS_INSTALL_ROOT}/lib/field-dns.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/field-dns.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/field-drive-system.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/field-drive-system.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/dns-admin-portal.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/dns-admin-portal.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/human-dossier.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/human-dossier.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/field-us-intel.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/field-us-intel.sh"
[[ "${NEXUS_FIELD_RF_SENTINEL:-0}" == "1" && -f "${NEXUS_INSTALL_ROOT}/lib/field-rf-sentinel.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/field-rf-sentinel.sh"
[[ -f "${NEXUS_INSTALL_ROOT}/lib/police-agency.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/police-agency.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/pest-arsenal.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/packet-oracle.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/nexus-settings.sh"
# shellcheck source=/dev/null
[[ -f "${NEXUS_INSTALL_ROOT}/lib/gatekeeper-enforce.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/gatekeeper-enforce.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/adblock-loader.sh"
nexus_settings_init
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/threat-panel.sh"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/panel-launch.sh"

[[ -f "${NEXUS_INSTALL_ROOT}/lib/front-hook.sh" ]] && {
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/front-hook.sh"
  nexus_front_hook_board
}
[[ -f "${NEXUS_INSTALL_ROOT}/lib/field-perimeter-shield.sh" ]] && {
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/field-perimeter-shield.sh"
}
nexus_vigil_init
nexus_predictive_init
nexus_shadow_init
nexus_privacy_harden
nexus_network_lockdown
nexus_firewall_takeover
nexus_firewall_ensure_self_access || true
nexus_kilroy_core_publish 2>/dev/null || true
nexus_hostess7_corroborate_integrity || true
declare -f nexus_field_dns_takeover_cycle >/dev/null 2>&1 && nexus_field_dns_takeover_cycle || true
declare -f nexus_dns_admin_firewall_permit >/dev/null 2>&1 && nexus_dns_admin_firewall_permit || true

nexus_log "INFO" "nexus-daemon" "NEXUS-Shield v${NEXUS_VERSION} ultra-stealth active (genius-only)"

start_module() {
  local name="$1"
  shift
  (
    set +e
    nexus_apply_cgroup_self
    "$@"
  ) &
  echo $! >"${NEXUS_STATE_DIR}/${name}.pid"
}

# Event-driven watchers (inotify) — no polling for file integrity/entropy
[[ "${NEXUS_SHADOW_WATCH:-1}" == "1" ]] && start_module shadow nexus_shadow_watch
[[ "${NEXUS_ENTROPY_WATCH:-1}" == "1" ]] && start_module entropy nexus_entropy_watch
[[ "${NEXUS_BEHAVIOR_WATCH:-1}" == "1" ]] && start_module behavior nexus_behavior_loop
[[ "${NEXUS_PRIVACY_GUARD:-1}" == "1" ]] && start_module privacy nexus_privacy_loop
[[ "${NEXUS_ADMIN_WINDOW_SHIELD:-1}" == "1" && -f "${NEXUS_INSTALL_ROOT}/lib/admin-window-shield.sh" ]] && {
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/admin-window-shield.sh"
  start_module admin-shield nexus_admin_window_shield_loop
}
[[ "${NEXUS_HARDWARE_WIRE:-${NEXUS_SMART_WIRE:-1}}" == "1" && -f "${NEXUS_INSTALL_ROOT}/lib/hardware-wire.sh" ]] && {
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/hardware-wire.sh"
  start_module hardware-wire nexus_hardware_wire_loop
}
[[ "${NEXUS_SMART_WIRE:-1}" == "1" && ! -f "${NEXUS_INSTALL_ROOT}/lib/hardware-wire.sh" && -f "${NEXUS_INSTALL_ROOT}/lib/smart-wire.sh" ]] && {
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/smart-wire.sh"
  start_module smart-wire nexus_smart_wire_loop
}
[[ "${NEXUS_FIELD_OPERATOR:-1}" == "1" && -f "${NEXUS_INSTALL_ROOT}/lib/field-operator.sh" ]] && {
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/field-operator.sh"
  start_module field-operator nexus_field_operator_loop
}
[[ "${SG_ROOT_SOVEREIGN_GUARD:-1}" == "1" ]] && start_module root-sovereign bash "${NEXUS_INSTALL_ROOT}/lib/root-sovereign-guard.sh"
[[ "${SG_FIELD_VIRUS_GUARD:-1}" == "1" && -f "${NEXUS_INSTALL_ROOT}/lib/field-virus-guard.sh" ]] && start_module field-virus bash "${NEXUS_INSTALL_ROOT}/lib/field-virus-guard.sh"
[[ "${NEXUS_VSYNC_LOCKER_GUARD:-1}" == "1" && -f "${NEXUS_INSTALL_ROOT}/lib/field-vsync-locker-guard.sh" ]] && start_module vsync-locker bash "${NEXUS_INSTALL_ROOT}/lib/field-vsync-locker-guard.sh"
[[ "${NEXUS_PACKET_ORACLE:-1}" == "1" ]] && start_module packet nexus_packet_loop
[[ "${NEXUS_FIELD_DNS:-1}" == "1" ]] && start_module field-dns nexus_field_dns_serve_loop
[[ "${NEXUS_FIELD_DHCP:-1}" == "1" ]] && start_module field-dhcp nexus_field_dhcp_serve_loop
[[ "${NEXUS_SOVEREIGN_TIME:-1}" == "1" ]] && start_module sovereign-time nexus_sovereign_time_serve_loop
[[ "${NEXUS_FIELD_NTP:-1}" == "1" ]] && start_module field-ntp nexus_field_ntp_serve_loop
[[ "${NEXUS_DNS_INTERNET_PULL:-1}" == "1" ]] && start_module dns-internet nexus_dns_internet_pull_loop
[[ "${NEXUS_DNS_ADMIN_PORTAL:-1}" == "1" ]] && start_module dns-admin nexus_dns_admin_serve_loop
[[ "${NEXUS_THREAT_PANEL:-1}" == "1" ]] && start_module panel nexus_threat_panel_serve_loop
[[ -f "${NEXUS_INSTALL_ROOT}/lib/queen-layer-boot.sh" ]] && {
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/queen-layer-boot.sh"
  nexus_queen_world_ensure || true
}
# shellcheck source=/dev/null
[[ -f "${NEXUS_INSTALL_ROOT}/lib/panel-browser.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/panel-browser.sh"
(
  nexus_await_curl_ready "$(nexus_panel_app_url 2>/dev/null || nexus_panel_url 2>/dev/null || echo 'http://127.0.0.1:9477/app')" 5 5
  if declare -f nexus_boot_c2_desktop >/dev/null 2>&1; then
    nexus_boot_c2_desktop
  elif declare -f nexus_panel_open_on_boot >/dev/null 2>&1; then
    nexus_panel_open_on_boot "$(nexus_panel_url 2>/dev/null || echo 'http://127.0.0.1:9477/field')"
  fi
) &

# Supervisor: vigil maintenance only — shadow verify handled by inotify
while true; do
  nexus_shutdown_heartbeat
  nexus_apply_permissions 2>/dev/null || true
  nexus_vigil_fix_perms 2>/dev/null || true
  nexus_vigil_prune_alerts
  nexus_vigil_recompute_mode
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/nexus-stray-task-guard.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/nexus-stray-task-guard.sh"
    nexus_stray_task_guard_cycle
  fi
  nexus_predictive_decay
  nexus_network_lockdown_verify
  nexus_firewall_verify
  nexus_firewall_ensure_self_access || true
  nexus_tamper_guard_cycle || true
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/friendly-guard.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/friendly-guard.sh"
    nexus_friendly_guard_verify_seal || nexus_log "ALERT" "friendly-guard" "SEAL_VERIFY_FAIL"
  fi
  nexus_threat_panel_publish
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/queen-layer-boot.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/queen-layer-boot.sh"
    nexus_queen_world_ensure || true
  fi
  if declare -f nexus_field_drive_publish >/dev/null 2>&1; then
    nexus_field_drive_publish
    nexus_field_drive_inbox_loop
  fi
  if declare -f nexus_field_attack_publish_deep >/dev/null 2>&1; then
    nexus_field_attack_publish_deep
  fi
  if declare -f nexus_host_attack_publish_deep >/dev/null 2>&1; then
    nexus_host_attack_publish_deep
  fi
  if declare -f nexus_planetary_observer_cycle >/dev/null 2>&1; then
    nexus_planetary_observer_cycle
  fi
  if declare -f nexus_field_rf_forever_enforce >/dev/null 2>&1; then
    nexus_field_rf_forever_enforce
  fi
  if [[ "${NEXUS_ADBLOCK:-0}" == "1" ]]; then
    nexus_adblock_apply 2>/dev/null || true
  fi
  if declare -f nexus_field_dns_enforce_cycle >/dev/null 2>&1; then
    nexus_field_dns_enforce_cycle
  fi
  if [[ "${NEXUS_THERMAL_GOVERNOR:-1}" == "1" ]] && [[ -f "${NEXUS_INSTALL_ROOT}/lib/thermal-governor.py" ]]; then
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      pythong "${NEXUS_INSTALL_ROOT}/lib/thermal-governor.py" cycle >/dev/null 2>&1 || true
  fi
  if [[ "${NEXUS_FIELD_SWITCH_SAFETY:-1}" == "1" ]] && [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-switch-safety.py" ]]; then
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      pythong "${NEXUS_INSTALL_ROOT}/lib/field-switch-safety.py" cycle >/dev/null 2>&1 || true
  fi
  if [[ "${NEXUS_FIELD_THERMAL_GUARD:-1}" == "1" ]] && [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-thermal-guard.py" ]]; then
    export NEXUS_FIELD_THERMAL_POLICY="${NEXUS_STATE_DIR}/field-thermal-guard-policy.env"
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      pythong "${NEXUS_INSTALL_ROOT}/lib/field-thermal-guard.py" cycle >/dev/null 2>&1 || true
  fi
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-depth-singularizer.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/field-depth-singularizer.sh"
    nexus_depth_singularizer_cycle
  fi
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-port-ddos.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/field-port-ddos.sh"
    nexus_port_ddos_cycle
  fi
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-packet-deinterlace.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/field-packet-deinterlace.sh"
    nexus_packet_deinterlace_cycle
  fi
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-plate-meld.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/field-plate-meld.sh"
    nexus_plate_meld_cycle
  elif [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-unified-bus.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/field-unified-bus.sh"
    nexus_unified_bus_cycle
  fi
  if declare -f nexus_perimeter_shield_cycle >/dev/null 2>&1; then
    nexus_perimeter_shield_cycle
  fi
  nexus_await_seconds "${NEXUS_VIGIL_MAINTAIN_INTERVAL:-5}" "${NEXUS_STATE_DIR}"
done
