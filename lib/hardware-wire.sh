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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/hardware-wire.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS Hardware Wire — detect and operate hooks for all field hardware.

nexus_hardware_wire_enabled() {
  [[ "${NEXUS_HARDWARE_WIRE:-${NEXUS_SMART_WIRE:-1}}" == "1" ]]
}

nexus_hardware_wire_once() {
  nexus_hardware_wire_enabled || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/hardware-wire.py"
  [[ -f "$py" ]] || return 0
  local pythong_bin="${NEXUS_PYTHONG:-$(nexus_resolve_pythong 2>/dev/null || true)}"
  [[ -n "$pythong_bin" ]] || return 0
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
    "$pythong_bin" "$py" enforce >/dev/null 2>&1 || true
}

nexus_hardware_wire_loop() {
  nexus_hardware_wire_enabled || return 0
  while true; do
    nexus_hardware_wire_once
    if declare -f nexus_field_loop_wait >/dev/null 2>&1; then
      nexus_field_loop_wait "${NEXUS_HARDWARE_WIRE_INTERVAL:-${NEXUS_SMART_WIRE_INTERVAL:-5}}" "${NEXUS_STATE_DIR}"
    else
      local interval="${NEXUS_HARDWARE_WIRE_INTERVAL:-${NEXUS_SMART_WIRE_INTERVAL:-5}}"
      nexus_await_seconds "$interval" "${NEXUS_STATE_DIR}" 2>/dev/null || sleep "$interval"
    fi
  done
}