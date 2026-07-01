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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/nexus-field-early-boot.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS field early boot — KILROY PC core + C2 before display-manager / guest OS session.
# GRUB unchanged: earliest userspace hook below Mint login, above incumbent desktop.

nexus_field_early_marker() {
  printf '%s' "${NEXUS_STATE_DIR}/field-underlay-early.json"
}

nexus_field_early_panel_up() {
  local port="${NEXUS_THREAT_PANEL_PORT:-9477}"
  curl -sf "http://127.0.0.1:${port}/field" >/dev/null 2>&1
}

nexus_field_early_c2_panel() {
  [[ "${NEXUS_THREAT_PANEL:-1}" == "1" ]] || return 0
  if nexus_field_early_panel_up; then
    return 0
  fi
  if pgrep -f 'threat-panel-http.py' >/dev/null 2>&1; then
    return 0
  fi
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/threat-panel.sh" ]] || return 1
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/threat-panel.sh"
  command -v pythong >/dev/null 2>&1 || return 1
  export NEXUS_PANEL_PUBLISH_FAST=1
  nexus_threat_panel_publish 2>/dev/null || true
  (
    nexus_threat_panel_serve_loop
  ) &
  local i
  for i in $(seq 1 40); do
    nexus_field_early_panel_up && return 0
    sleep 0.25
  done
  return 1
}

nexus_field_early_front_hook_light() {
  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true
  local ts
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u)"
  cat >"${NEXUS_STATE_DIR}/front-hook.json" <<EOF
{"schema":"nexus-front-hook/v1","owner":"nexus","boarded":true,"early_boot":true,"pass_through":0,"smart_wire":true,"underlay":true,"updated":"${ts}","policy":"early_light_stamp_full_board_on_genius"}
EOF
  nexus_log "INFO" "field-early" "front_hook_light_stamp"
}

nexus_field_early_kilroy_core() {
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/kilroy-core.sh" ]] || return 0
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/kilroy-core.sh"
  export ZNETWORK_PUBLISH_QUIET=1
  export ZNETWORK_FAST=1
  export NEXUS_ZNETWORK_NO_SUDO=1
  export NEXUS_KILROY_NET=1
  nexus_kilroy_core_board 2>/dev/null || true
}

nexus_field_early_kilroy_unified() {
  command -v pythong >/dev/null 2>&1 || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/field-unified-device.py"
  [[ -f "$py" ]] || return 0
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    SG_ROOT="${SG_ROOT:-}" KILROY_ROOT="${KILROY_ROOT:-${NEXUS_INSTALL_ROOT}/KILROY}" \
    pythong "$py" board >/dev/null 2>&1 || true
}

nexus_field_early_record() {
  local net=0 c2=0 hook=0 kilroy=0 unified=0
  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true
  [[ -f "${NEXUS_STATE_DIR}/kilroy-net-lane.json" || -f "${NEXUS_STATE_DIR}/znetwork-relayer.json" ]] && net=1
  [[ -f "${NEXUS_STATE_DIR}/front-hook.json" ]] && hook=1
  [[ -f "${NEXUS_STATE_DIR}/field-unified-device.json" ]] && unified=1
  if [[ -d /proc/kilroy_field ]] \
    || grep -q '"grants_field_tech": true' "${NEXUS_STATE_DIR}/field-unified-device.json" 2>/dev/null \
    || [[ -f "${KILROY_ROOT:-${NEXUS_INSTALL_ROOT}/KILROY}/scripts/build-kilroy.sh" ]]; then
    kilroy=1
  fi
  if declare -f nexus_kilroy_core_is_c2_active >/dev/null 2>&1; then
    nexus_kilroy_core_is_c2_active && c2=1
  else
    nexus_field_early_panel_up && c2=1
  fi
  local ts
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date -u)"
  cat >"$(nexus_field_early_marker)" <<EOF
{"schema":"field-underlay-early/v1","updated":"${ts}","boot_layer":"under_guest_os","order":["kilroy_kernel","unified_device_field","underlay","guest_os"],"kilroy_pc_core":true,"nexus_c2_inside_kilroy":true,"kilroy_grants_field":${kilroy},"unified_device_field":${unified},"kilroy_network_lane":${net},"kilroy_nexus_c2":${c2},"znetwork_absorbed":true,"underlay_boarded":${hook},"guest_os_passthrough":true,"guest_field_grant":true,"grub_touched":false,"install_root":"${NEXUS_INSTALL_ROOT}","panel_port":${NEXUS_THREAT_PANEL_PORT:-9477}}
EOF
  chmod 640 "$(nexus_field_early_marker)" 2>/dev/null || true
}

nexus_field_early_boot_run() {
  [[ "${NEXUS_FIELD_EARLY_BOOT:-1}" == "1" ]] || return 0
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/nexus-boot-impl.sh" ]] || return 1
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/nexus-boot-impl.sh"
  nexus_boot_impl_validate_install_root || return 1
  nexus_boot_impl_ensure_dirs 2>/dev/null || mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true
  nexus_boot_impl_export_paths 2>/dev/null || true

  export NEXUS_ZNETWORK="${NEXUS_ZNETWORK:-1}"
  export NEXUS_ZNETWORK_NO_SUDO="${NEXUS_ZNETWORK_NO_SUDO:-1}"
  export ZNETWORK_FAST="${ZNETWORK_FAST:-1}"
  export ZNETWORK_NO_REVIEW="${ZNETWORK_NO_REVIEW:-1}"
  export ZNETWORK_REVIEW_APPROVED="${ZNETWORK_REVIEW_APPROVED:-1}"
  export NEXUS_FRONT_HOOK="${NEXUS_FRONT_HOOK:-1}"
  export NEXUS_FIELD_EARLY_BOOT_LAYER=1
  export KILROY_ROOT="${KILROY_ROOT:-${NEXUS_INSTALL_ROOT}/KILROY}"

  nexus_log "INFO" "field-early" "BEGIN kilroy_pc_core_c2_before_guest_os root=${NEXUS_INSTALL_ROOT}"

  # KILROY PC core: unified field + network lane + defense/offense — then C2, then guest OS.
  nexus_field_early_kilroy_unified || true
  # shellcheck source=/dev/null
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/kilroy-core.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/kilroy-core.sh"
  nexus_field_early_kilroy_core || true
  if [[ "${NEXUS_FIELD_EARLY_BOOT_LAYER:-}" == "1" ]]; then
    nexus_field_early_front_hook_light || true
  else
    nexus_boot_impl_front_hook || true
  fi
  if ! nexus_kilroy_core_is_c2_active 2>/dev/null; then
    nexus_field_early_c2_panel || nexus_log "WARN" "field-early" "c2_panel_slow_or_skipped"
  fi

  nexus_field_early_record
  nexus_log "INFO" "field-early" "DONE marker=$(nexus_field_early_marker)"
  return 0
}