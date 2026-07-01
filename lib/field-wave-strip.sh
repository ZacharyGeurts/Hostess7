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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-wave-strip.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Field wave strip — board voltage-is-voltage doctrine.
set -euo pipefail

nexus_wave_strip_board() {
  local root="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  local py="${root}/lib/field-wave-strip.py"
  [[ -f "$py" ]] || return 0
  NEXUS_INSTALL_ROOT="${root}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}" \
    pythong "$py" board 2>/dev/null || pythong "$py" json >/dev/null || true
}

nexus_wave_shed_excess() {
  local root="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  local py="${root}/lib/field-wave-shed.py"
  [[ -f "$py" ]] || return 0
  NEXUS_INSTALL_ROOT="${root}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}" \
    NEXUS_WAVE_SHED_APPLY="${NEXUS_WAVE_SHED_APPLY:-0}" \
    pythong "$py" shed 2>/dev/null || true
}

