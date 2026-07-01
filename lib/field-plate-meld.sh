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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-plate-meld.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Plate meld — fuse all plates under flock each vigil cycle.

nexus_plate_meld_enabled() {
  [[ "${NEXUS_PLATE_MELD:-1}" == "1" ]]
}

nexus_network_stack_pre_meld() {
  [[ "${NEXUS_NETWORK_STACK_MELD:-1}" == "1" ]] || return 0
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/znetwork-field.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/znetwork-field.sh"
    ZNETWORK_PUBLISH_QUIET=1 nexus_znetwork_publish 2>/dev/null || true
  fi
  if [[ "${NEXUS_IRON_PLATE_MELD_REFRESH:-1}" == "1" ]] && command -v pythong >/dev/null 2>&1 \
    && [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-operator.py" ]]; then
    NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      pythong "${NEXUS_INSTALL_ROOT}/lib/field-operator.py" iron-plate >/dev/null 2>&1 || true
  fi
  if [[ "${NEXUS_CONNECTION_GATEKEEPER:-1}" == "1" ]] && [[ -f "${NEXUS_INSTALL_ROOT}/lib/packet-oracle.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/packet-oracle.sh"
    declare -f nexus_connection_gatekeeper_publish >/dev/null 2>&1 \
      && nexus_connection_gatekeeper_publish 2>/dev/null || true
  fi
  if [[ "${NEXUS_LOGIC_GATE:-1}" == "1" ]] && command -v pythong >/dev/null 2>&1 \
    && [[ -f "${NEXUS_INSTALL_ROOT}/lib/nexus-logic-gate.py" ]]; then
    NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      pythong "${NEXUS_INSTALL_ROOT}/lib/nexus-logic-gate.py" json \
      >"${NEXUS_STATE_DIR}/nexus-logic-gate-runtime.json.tmp" 2>/dev/null \
      && mv -f "${NEXUS_STATE_DIR}/nexus-logic-gate-runtime.json.tmp" \
        "${NEXUS_STATE_DIR}/nexus-logic-gate-runtime.json" 2>/dev/null || true
  fi
}

nexus_plate_meld_cycle() {
  nexus_plate_meld_enabled || return 0
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/ironclad-reality-field.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/ironclad-reality-field.sh"
    nexus_ironclad_reality_field_cycle
  fi
  nexus_network_stack_pre_meld
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-sense-package.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/field-sense-package.sh"
    nexus_sense_package_cycle
  fi
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-firmware-threat.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/field-firmware-threat.sh"
    nexus_firmware_threat_cycle
  fi
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-kernel-meld.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/field-kernel-meld.sh"
    nexus_kernel_meld_cycle
  fi
  local py="${NEXUS_INSTALL_ROOT}/lib/field-plate-meld.py"
  [[ -f "$py" ]] || return 0
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    pythong "$py" fuse >/dev/null 2>&1 \
    || NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      pythong "$py" meld >/dev/null 2>&1 || true
}