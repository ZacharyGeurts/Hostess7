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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-port-ddos.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Port & WiFi DDoS shield — wave view thermals + entropy at network edge.

nexus_port_ddos_enabled() {
  [[ "${NEXUS_PORT_DDOS_SHIELD:-1}" == "1" ]]
}

nexus_port_ddos_cycle() {
  nexus_port_ddos_enabled || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/field-port-ddos-shield.py"
  [[ -f "$py" ]] || return 0
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    NEXUS_PORT_DDOS_ENFORCE="${NEXUS_PORT_DDOS_ENFORCE:-1}" \
    pythong "$py" cycle >/dev/null 2>&1 || true
}