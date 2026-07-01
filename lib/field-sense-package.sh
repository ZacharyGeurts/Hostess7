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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-sense-package.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Sense package meld — witness Final_Eye · Final_Ear · ZOCR · World_Redata each cycle.

nexus_sense_package_enabled() {
  [[ "${NEXUS_SENSE_PACKAGE:-1}" == "1" ]]
}

nexus_sense_package_cycle() {
  nexus_sense_package_enabled || return 0
  # Plate → eye/ear/mouth goldmine hot-read before sense witness meld
  if declare -F nexus_ironclad_immediate_publish >/dev/null 2>&1; then
    nexus_ironclad_immediate_publish
  elif [[ -f "${NEXUS_INSTALL_ROOT}/lib/ironclad-immediate.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/ironclad-immediate.sh"
    nexus_ironclad_immediate_publish
  fi
  local py="${NEXUS_INSTALL_ROOT}/lib/field-sense-package-meld.py"
  [[ -f "$py" ]] || return 0
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    SG_ROOT="${SG_ROOT:-}" \
    FINAL_EYE_ROOT="${FINAL_EYE_ROOT:-}" \
    FINAL_EAR_ROOT="${FINAL_EAR_ROOT:-}" \
    ZOCR_ROOT="${ZOCR_ROOT:-}" \
    ZNEWOCR_ROOT="${ZNEWOCR_ROOT:-}" \
    WORLD_REDATA_ROOT="${WORLD_REDATA_ROOT:-}" \
    HOSTESS7_ROOT="${HOSTESS7_ROOT:-}" \
    HOSTESS7_TEAM_FIELD="${HOSTESS7_TEAM_FIELD:-}" \
    HOSTESS7_TEAM1_FIELD="${HOSTESS7_TEAM1_FIELD:-}" \
    HOSTESS7_NEXUS_CACHE="${HOSTESS7_NEXUS_CACHE:-}" \
    ZOCR_PORT="${ZOCR_PORT:-${FINAL_EYE_PORT:-9479}}" \
    WORLD_REDATA_WEB_PORT="${WORLD_REDATA_WEB_PORT:-9478}" \
    pythong "$py" meld >/dev/null 2>&1 || true
}