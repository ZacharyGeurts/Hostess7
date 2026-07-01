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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/kilroy-core.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# KILROY PC core — boots the field, loads guest OS normally inside the grant.
# Network (ex-ZNetwork), defense, and offense are owned here — not separate stack layers.

if [[ -f "${NEXUS_INSTALL_ROOT:-}/lib/kilroy-resolve.sh" ]]; then
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/kilroy-resolve.sh"
elif [[ -f "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/kilroy-resolve.sh" ]]; then
  # shellcheck source=/dev/null
  source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/kilroy-resolve.sh"
fi

nexus_kilroy_core_marker() {
  printf '%s' "${NEXUS_STATE_DIR}/kilroy-core.json"
}

nexus_kilroy_core_net_marker() {
  printf '%s' "${NEXUS_STATE_DIR}/kilroy-net-lane.json"
}

nexus_kilroy_core_c2_marker() {
  printf '%s' "${NEXUS_STATE_DIR}/kilroy-nexus-c2.json"
}

nexus_kilroy_core_loopback_marker() {
  printf '%s' "${NEXUS_STATE_DIR}/kilroy-loopback.json"
}

nexus_kilroy_core_resolve() {
  nexus_kilroy_export "${SG_ROOT:-}" 2>/dev/null || true
  export KILROY_ROOT="${KILROY_ROOT:-${NEXUS_INSTALL_ROOT}/KILROY}"
  export KILROY_PC_CORE=1
  export KILROY_OWNS_NETWORK=1
  export KILROY_OWNS_DEFENSE=1
  export KILROY_OWNS_OFFENSE=1
  export KILROY_OWNS_NEXUS_C2=1
  export KILROY_KERNEL_UNLOCKED="${KILROY_KERNEL_UNLOCKED:-1}"
  export KILROY_WAR_POSTURE=1
  export KILROY_AI_DEFAULT_MODE="${KILROY_AI_DEFAULT_MODE:-war}"
  export KILROY_DEFENSIVE_ONLY="${KILROY_DEFENSIVE_ONLY:-1}"
  export KILROY_WAR_SCOPE="${KILROY_WAR_SCOPE:-defensive_perimeter}"
  export KILROY_HOSTILE_INSIDE="${KILROY_HOSTILE_INSIDE:-0}"
  export KILROY_SELF_HARM_FORBIDDEN="${KILROY_SELF_HARM_FORBIDDEN:-1}"
  export KILROY_EXISTENTIAL_PROTECTION="${KILROY_EXISTENTIAL_PROTECTION:-1}"
  export KILROY_LOOPBACK_SANCTUARY="${KILROY_LOOPBACK_SANCTUARY:-1}"
  export NEXUS_FIELD_HOSTILE_SCOPE="${NEXUS_FIELD_HOSTILE_SCOPE:-defensive_ingress_only}"
}

nexus_kilroy_core_panel_up() {
  local port="${NEXUS_THREAT_PANEL_PORT:-9477}"
  curl -sf "http://127.0.0.1:${port}/field" >/dev/null 2>&1
}

nexus_kilroy_core_nexus_c2() {
  [[ "${NEXUS_THREAT_PANEL:-1}" == "1" ]] || return 0
  local port="${NEXUS_THREAT_PANEL_PORT:-9477}"
  local up=0 theme="black_emerald_rose_2026"
  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true

  if nexus_kilroy_core_panel_up; then
    up=1
  elif pgrep -f 'threat-panel-http.py' >/dev/null 2>&1; then
    up=1
  elif [[ -f "${NEXUS_INSTALL_ROOT}/lib/threat-panel.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/threat-panel.sh"
    if command -v pythong >/dev/null 2>&1; then
      export NEXUS_PANEL_PUBLISH_FAST="${NEXUS_PANEL_PUBLISH_FAST:-1}"
      nexus_threat_panel_publish 2>/dev/null || true
      if ! nexus_kilroy_core_panel_up; then
        (
          nexus_threat_panel_serve_loop
        ) &
        local i
        for i in $(seq 1 40); do
          nexus_kilroy_core_panel_up && { up=1; break; }
          sleep 0.25
        done
      else
        up=1
      fi
    fi
  fi

  local ts
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u)"
  cat >"$(nexus_kilroy_core_c2_marker)" <<EOF
{"schema":"kilroy-nexus-c2/v1","owner":"kilroy_core","role":"field_tech_monitoring_panel","theme":"${theme}","palette":"black_green_pink","panel_port":${port},"panel_url":"http://127.0.0.1:${port}/field","command_url":"http://127.0.0.1:${port}/command","module":"lib/threat-panel.sh","http":"lib/threat-panel-http.py","active":${up},"monitoring":"all_out_field_tech","updated":"${ts}"}
EOF
  [[ "$up" -eq 1 ]]
}

nexus_kilroy_core_unified_field() {
  command -v pythong >/dev/null 2>&1 || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/field-unified-device.py"
  [[ -f "$py" ]] || return 0
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    SG_ROOT="${SG_ROOT:-}" KILROY_ROOT="${KILROY_ROOT:-}" \
    pythong "$py" board >/dev/null 2>&1 || true
}

nexus_kilroy_core_znetwork_impl() {
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/znetwork-field.sh" ]] || return 0
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/znetwork-field.sh"
}

nexus_kilroy_core_network_lane() {
  [[ "${NEXUS_KILROY_NET:-1}" == "1" ]] || return 0
  nexus_kilroy_core_znetwork_impl || return 0
  export KILROY_NET_LANE=1
  export ZNETWORK_PUBLISH_QUIET="${ZNETWORK_PUBLISH_QUIET:-1}"
  export ZNETWORK_FAST="${ZNETWORK_FAST:-1}"
  export NEXUS_ZNETWORK="${NEXUS_ZNETWORK:-1}"
  export NEXUS_ZNETWORK_NO_SUDO="${NEXUS_ZNETWORK_NO_SUDO:-1}"
  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true

  if declare -f nexus_znetwork_relayer_already_active >/dev/null 2>&1 \
    && ! nexus_znetwork_relayer_already_active 2>/dev/null; then
    local ts
    ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u)"
    cat >"${NEXUS_STATE_DIR}/znetwork-relayer.json" <<EOF
{"schema":"znetwork-relayer/v1","active":true,"owner":"kilroy_core","early_boot":true,"mode":"ACTIVE","posture":"kilroy_network_lane","updated":"${ts}"}
EOF
  fi

  if declare -f nexus_znetwork_publish_quiet >/dev/null 2>&1; then
    nexus_znetwork_publish_quiet 2>/dev/null || true
  elif declare -f nexus_znetwork_publish >/dev/null 2>&1; then
    nexus_znetwork_publish 2>/dev/null || true
  fi

  local active=0 mode="unknown"
  if [[ -f "${NEXUS_STATE_DIR}/znetwork-relayer.json" ]]; then
    active=1
    mode="kilroy_network_lane"
  fi
  if declare -f nexus_znetwork_is_running >/dev/null 2>&1 && nexus_znetwork_is_running 2>/dev/null; then
    active=1
    mode="relayer_active"
  fi
  local ts
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u)"
  cat >"$(nexus_kilroy_core_net_marker)" <<EOF
{"schema":"kilroy-net-lane/v1","owner":"kilroy_core","absorbed":"znetwork","active":${active},"mode":"${mode}","netlink_slots":"16-19","updated":"${ts}"}
EOF
}

nexus_kilroy_core_network_startup() {
  nexus_kilroy_core_znetwork_impl || return 0
  export KILROY_NET_LANE=1
  if declare -f nexus_znetwork_startup_with_us >/dev/null 2>&1; then
    nexus_znetwork_startup_with_us 2>/dev/null || true
  fi
  nexus_kilroy_core_network_lane || true
}

nexus_kilroy_core_loopback() {
  [[ "${NEXUS_KILROY_LOOPBACK:-1}" == "1" ]] || return 0
  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true
  export KILROY_LOOPBACK_AUTHORITY="127.0.0.1"
  if command -v pythong >/dev/null 2>&1 && [[ -f "${NEXUS_INSTALL_ROOT}/lib/kilroy-loopback.py" ]]; then
    NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      pythong "${NEXUS_INSTALL_ROOT}/lib/kilroy-loopback.py" board >/dev/null 2>&1 || true
    return 0
  fi
  local ts active=0
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u)"
  nexus_kilroy_core_panel_up && active=1
  cat >"$(nexus_kilroy_core_loopback_marker)" <<EOF
{"schema":"kilroy-loopback/v1","owner":"kilroy_core","loopback_authority":"127.0.0.1","transparent":true,"guest_unmodified":true,"active":${active},"updated":"${ts}"}
EOF
}

nexus_kilroy_core_defense_offense() {
  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true
  local attack=0 pest=0
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-attack-kit.sh" ]] && attack=1
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/pest-arsenal.sh" ]] && pest=1
  local ts
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u)"
  cat >"${NEXUS_STATE_DIR}/kilroy-defense-offense.json" <<EOF
{"schema":"kilroy-defense-offense/v1","owner":"kilroy_core","war_scope":"defensive_perimeter","defensive_only":true,"hostile_inside":false,"self_harm_forbidden":true,"existential_protection":true,"defense":["self_defensive_field_die","tamper_verify","loopback_sanctuary","firewall_sentinel","seal_vault","ingress_gatekeeper"],"offense":["field_attack_kit","relayer_retaliation"],"offense_scope":"reactive_confirmed_threat_only","attack_kit_present":${attack},"pest_arsenal_present":${pest},"guest_cannot_disable":true,"updated":"${ts}"}
EOF
}

nexus_kilroy_core_record() {
  local net=0 unified=0 kilroy=0 c2=0 loopback=0
  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true
  [[ -f "$(nexus_kilroy_core_net_marker)" ]] && net=1
  [[ -f "$(nexus_kilroy_core_c2_marker)" ]] && c2=1
  [[ -f "$(nexus_kilroy_core_loopback_marker)" ]] && loopback=1
  nexus_kilroy_core_panel_up && c2=1
  [[ -f "${NEXUS_STATE_DIR}/field-unified-device.json" ]] && unified=1
  if [[ -d /proc/kilroy_field ]] \
    || grep -q '"grants_field_tech": true' "${NEXUS_STATE_DIR}/field-unified-device.json" 2>/dev/null \
    || [[ -f "${KILROY_ROOT:-}/scripts/build-kilroy.sh" ]]; then
    kilroy=1
  fi
  local ts port="${NEXUS_THREAT_PANEL_PORT:-9477}"
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u)"
  cat >"$(nexus_kilroy_core_marker)" <<EOF
{"schema":"kilroy-core/v1","updated":"${ts}","role":"pc_core","motto":"KILROY defensive kernel — guard ingress, sanctuary inside, boot-ready","boot_order":["kilroy_kernel","unified_device_field","underlay","guest_os"],"loopback_authority":"127.0.0.1","loopback_sovereign":${loopback},"kernel_unlocked":true,"defensive_only":true,"war_scope":"defensive_perimeter","hostile_inside":false,"self_harm_forbidden":true,"existential_protection":true,"boot_ready":true,"kilroy_grants_field":${kilroy},"unified_device_field":${unified},"network_lane":${net},"nexus_c2":${c2},"nexus_c2_owner":"kilroy_core","nexus_c2_panel":"http://127.0.0.1:${port}/field","nexus_c2_theme":"black_green_pink","network_owner":"kilroy_core","znetwork_absorbed":true,"defense_offense":"kilroy_core","war_posture":true,"ai_default_mode":"war","guest_os_passthrough":true,"guest_field_grant":true,"install_root":"${NEXUS_INSTALL_ROOT}"}
EOF
  chmod 640 "$(nexus_kilroy_core_marker)" 2>/dev/null || true
}

nexus_kilroy_core_brain() {
  [[ "${NEXUS_KILROY_BRAIN:-1}" == "1" ]] || return 0
  command -v pythong >/dev/null 2>&1 || return 0
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/kilroy-field-brain.py" ]] || return 0
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    KILROY_ROOT="${KILROY_ROOT:-}" HOSTESS7_ROOT="${HOSTESS7_ROOT:-}" \
    pythong "${NEXUS_INSTALL_ROOT}/lib/kilroy-field-brain.py" board >/dev/null 2>&1 || true
}

nexus_kilroy_core_boot_services() {
  [[ "${NEXUS_KILROY_BOOT_SERVICES:-1}" == "1" ]] || return 0
  command -v pythong >/dev/null 2>&1 || return 0
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/kilroy-boot-services.py" ]] || return 0
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    pythong "${NEXUS_INSTALL_ROOT}/lib/kilroy-boot-services.py" board >/dev/null 2>&1 || true
}

nexus_kilroy_core_board() {
  nexus_kilroy_core_resolve || true
  nexus_kilroy_core_unified_field || true
  nexus_kilroy_core_loopback || true
  nexus_kilroy_core_boot_services || true
  nexus_kilroy_core_brain || true
  nexus_kilroy_core_nexus_c2 || true
  nexus_kilroy_core_network_lane || true
  nexus_kilroy_core_defense_offense || true
  nexus_kilroy_core_record
}

nexus_kilroy_core_publish() {
  nexus_kilroy_core_resolve || true
  nexus_kilroy_core_loopback || true
  nexus_kilroy_core_boot_services || true
  nexus_kilroy_core_brain || true
  nexus_kilroy_core_nexus_c2 || true
  nexus_kilroy_core_network_lane || true
  nexus_kilroy_core_defense_offense || true
  nexus_kilroy_core_record
}

nexus_kilroy_core_is_loopback_active() {
  [[ -f "$(nexus_kilroy_core_loopback_marker)" ]] && return 0
  nexus_kilroy_core_panel_up && return 0
  return 1
}

nexus_kilroy_core_is_c2_active() {
  nexus_kilroy_core_panel_up && return 0
  [[ -f "$(nexus_kilroy_core_c2_marker)" ]] && return 0
  return 1
}

nexus_kilroy_core_is_network_active() {
  [[ -f "$(nexus_kilroy_core_net_marker)" ]] && return 0
  [[ -f "${NEXUS_STATE_DIR}/znetwork-relayer.json" ]] && return 0
  [[ -f "${NEXUS_STATE_DIR}/znetwork-running.marker" ]] && return 0
  return 1
}