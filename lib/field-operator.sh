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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-operator.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Operator — field workhorse (IRQ, DMA, Smart Connective Iron Plate).
set -euo pipefail

nexus_field_operator_once() {
  [[ "${NEXUS_FIELD_OPERATOR:-1}" == "1" ]] || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/field-operator.py"
  [[ -f "$py" ]] || return 0
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}" \
    SG_ROOT="${SG_ROOT:-}" pythong "$py" tick >/dev/null 2>&1 || true
}

nexus_field_operator_loop() {
  [[ "${NEXUS_FIELD_OPERATOR:-1}" == "1" ]] || return 0
  local interval="${NEXUS_FIELD_OPERATOR_INTERVAL:-300}"
  while true; do
    nexus_field_operator_once
    sleep "$interval"
  done
}