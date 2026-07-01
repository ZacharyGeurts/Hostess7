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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/native-layer.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS Native Layer — THE native down to BIOS witness; no flash; everything lives with us.

nexus_native_layer_enabled() {
  [[ "${NEXUS_NATIVE_LAYER:-1}" == "1" ]]
}

nexus_native_layer_board() {
  nexus_native_layer_enabled || return 0
  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/native-layer.py" ]]; then
    SG_ROOT="${SG_ROOT:-$(cd "${NEXUS_INSTALL_ROOT}/.." 2>/dev/null && pwd)}"
    KILROY_ROOT="${KILROY_ROOT:-${SG_ROOT}/KILROY}"
    QUEEN_ROOT="${QUEEN_ROOT:-${SG_ROOT}/NewLatest/Queen}"
    NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
    NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    SG_ROOT="${SG_ROOT}" \
    KILROY_ROOT="${KILROY_ROOT}" \
    QUEEN_ROOT="${QUEEN_ROOT}" \
      pythong "${NEXUS_INSTALL_ROOT}/lib/native-layer.py" board >/dev/null 2>&1 || true
  fi
  nexus_log "INFO" "native-layer" "BOARD_HIT policy=witness_bios_no_flash lives_with_us=1"
}