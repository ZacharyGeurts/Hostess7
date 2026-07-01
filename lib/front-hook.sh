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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/front-hook.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS Front Hook — hit the board first; never pass hooks downstream.

nexus_front_hook_enabled() {
  [[ "${NEXUS_FRONT_HOOK:-1}" == "1" ]]
}

nexus_front_hook_pass_through() {
  [[ "${NEXUS_HOOK_PASS_THROUGH:-0}" == "1" ]]
}

nexus_front_hook_board() {
  nexus_front_hook_enabled || return 0
  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true
  local ts pass=0
  ts="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  nexus_front_hook_pass_through && pass=1
  cat >"${NEXUS_STATE_DIR}/front-hook.json" <<EOF
{"schema":"nexus-front-hook/v1","owner":"nexus","boarded":true,"pass_through":${pass},"smart_wire":true,"hardware_wire":true,"ai_integration_hook":true,"human_integration":false,"updated":"${ts}","policy":"front_hook_never_pass_off"}
EOF
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/cpu-vulnerability-shield.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/cpu-vulnerability-shield.sh"
    nexus_cpu_vuln_shield_board
  fi
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/native-layer.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/native-layer.sh"
    nexus_native_layer_board
  fi
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/ai-integration-hook.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/ai-integration-hook.sh"
    nexus_ai_integration_hook_board
  fi
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/hardware-wire.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/hardware-wire.sh"
    nexus_hardware_wire_once
  elif [[ -f "${NEXUS_INSTALL_ROOT}/lib/smart-wire.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/smart-wire.sh"
    nexus_smart_wire_once
  fi
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/admin-window-shield.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/admin-window-shield.sh"
    nexus_admin_window_shield_once
  fi
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-wave-strip.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/field-wave-strip.sh"
    nexus_wave_strip_board
  fi
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-power-ledger.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/field-power-ledger.sh"
    nexus_power_ledger_board
  fi
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-underlay.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/field-underlay.sh"
    nexus_field_underlay_board
  fi
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-perimeter-shield.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/field-perimeter-shield.sh"
    nexus_perimeter_shield_board
  fi
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-keyboard-sovereign.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/field-keyboard-sovereign.sh"
    nexus_keyboard_sovereign_engage
  fi
  nexus_log "INFO" "front-hook" "BOARD_HIT owner=nexus pass_through=${pass} smart_wire=1 underlay=1 tristate=1 perimeter=1 keyboard_sovereign=1"
}