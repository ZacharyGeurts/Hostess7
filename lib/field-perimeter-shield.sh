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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-perimeter-shield.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS Field Perimeter Shield — board network/wifi/BT/USB/ethernet/power/physical layers.
set -euo pipefail

nexus_perimeter_shield_board() {
  local root="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  local py="${root}/lib/field-perimeter-shield.py"
  local enforce="${root}/lib/field-perimeter-enforce.sh"
  [[ -f "$py" ]] || return 0
  if [[ "$(id -u)" -eq 0 && "${NEXUS_PERIMETER_APPLY:-0}" == "1" && -f "$enforce" ]]; then
    # shellcheck source=/dev/null
    source "$enforce"
    nexus_perimeter_apply_all 2>/dev/null || true
  fi
  NEXUS_INSTALL_ROOT="${root}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}" \
    NEXUS_PERIMETER_APPLY="${NEXUS_PERIMETER_APPLY:-0}" \
    pythong "$py" board 2>/dev/null || pythong "$py" json >/dev/null || true
}

nexus_perimeter_shield_cycle() {
  [[ "${NEXUS_FIELD_PERIMETER:-1}" == "1" ]] || return 0
  nexus_perimeter_shield_board
}