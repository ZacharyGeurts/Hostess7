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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/nexus-field-os.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS Field OS — single-tree paths, Grok16/GPY-16/AmmoLang, underlay witness.

nexus_field_os_export_paths() {
  local root="${NEXUS_INSTALL_ROOT:-}"
  [[ -n "$root" ]] || return 0

  export SG_ROOT="${SG_ROOT:-$root}"
  export GROK16_ROOT="${GROK16_ROOT:-${root}/Grok16}"
  export G16_PREFIX="${G16_PREFIX:-$GROK16_ROOT}"
  export GPY16_ROOT="${GPY16_ROOT:-${GROK16_ROOT}/python}"
  export GROKPY_ROOT="${GROKPY_ROOT:-$GPY16_ROOT}"
  export PYTHONG_ROOT="${PYTHONG_ROOT:-$GPY16_ROOT}"
  export QUEEN_ROOT="${QUEEN_ROOT:-${root}/Queen}"
  export HOSTESS7_ROOT="${HOSTESS7_ROOT:-${root}/Hostess7}"
  export KILROY_ROOT="${KILROY_ROOT:-${root}/KILROY}"

  export GPY16_PROFILE="${GPY16_PROFILE:-fastest}"
  export GROKPY_PROFILE="${GROKPY_PROFILE:-fastest}"
  export GPY16_FAST="${GPY16_FAST:-1}"
  export GPY16_CACHE="${GPY16_CACHE:-1}"
  export G16_OPTIMAL_COMBINATRONICS_AT_COMPILE="${G16_OPTIMAL_COMBINATRONICS_AT_COMPILE:-0}"
  export G16_AI_PROFILE="${G16_AI_PROFILE:-ai_agent}"
  export AML_BUILD="${AML_BUILD:-1}"
  export AML_FAST="${AML_FAST:-1}"

  local path_add="${GROK16_ROOT}/bin:${G16_PREFIX}/bin:${G16_PREFIX}/libexec/grok16:${root}/bin"
  case ":${PATH}:" in
    *":${GROK16_ROOT}/bin:"*) ;;
    *) export PATH="${path_add}:${PATH}" ;;
  esac

  if [[ -x "${GROK16_ROOT}/bin/gpy-16" ]]; then
    export GPY16_DRIVER="${GPY16_DRIVER:-${GROK16_ROOT}/bin/gpy-16}"
    export NEXUS_PYTHONG="${NEXUS_PYTHONG:-${GPY16_DRIVER}}"
  fi
}

nexus_field_os_underlay_witness() {
  local py="${NEXUS_PYTHONG:-$(nexus_resolve_pythong 2>/dev/null || true)}"
  [[ -n "$py" ]] || py="$(command -v python3 2>/dev/null || true)"
  [[ -n "$py" ]] || return 0

  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-underlay-surface.py" ]]; then
    NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      "$py" "${NEXUS_INSTALL_ROOT}/lib/field-underlay-surface.py" json \
      >>"${NEXUS_STATE_DIR}/boot-impl.log" 2>&1 || true
  fi

  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-underlay-hotkey.py" ]]; then
    NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      "$py" "${NEXUS_INSTALL_ROOT}/lib/field-underlay-hotkey.py" install \
      >>"${NEXUS_STATE_DIR}/boot-impl.log" 2>&1 || true
  fi

  nexus_log "INFO" "nexus-os" "underlay_witness ok"
}

nexus_field_os_build_clean() {
  local py="${NEXUS_PYTHONG:-$(nexus_resolve_pythong 2>/dev/null || true)}"
  [[ -n "$py" ]] || py="$(command -v python3 2>/dev/null || true)"
  local script="${NEXUS_INSTALL_ROOT}/lib/nexus-field-build-cleanup.py"
  [[ -f "$script" && -n "$py" ]] || return 1
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    "$py" "$script" run
}

nexus_field_os_sovereign_build() {
  if [[ "${AML_BUILD:-1}" != "0" && -f "${NEXUS_INSTALL_ROOT}/lib/ammolang-run.sh" ]]; then
    nexus_field_os_export_paths
    NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      GROK16_ROOT="${GROK16_ROOT}" G16_PREFIX="${G16_PREFIX}" \
      AML_BUILD=1 AML_FAST=1 \
      bash "${NEXUS_INSTALL_ROOT}/lib/ammolang-run.sh" sovereign
    return $?
  fi
  local py="${NEXUS_PYTHONG:-$(nexus_resolve_pythong 2>/dev/null || true)}"
  [[ -n "$py" ]] || py="$(command -v python3 2>/dev/null || true)"
  local script="${NEXUS_INSTALL_ROOT}/lib/field-ammolang-build.py"
  [[ -f "$script" && -n "$py" ]] || return 1
  nexus_field_os_export_paths
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    GROK16_ROOT="${GROK16_ROOT}" G16_PREFIX="${G16_PREFIX}" \
    AML_BUILD=1 AML_FAST=1 \
    "$py" "$script" run "${NEXUS_INSTALL_ROOT}/library/dewey/000-computer-science/ammolang/sovereign_build.aml"
}

nexus_field_os_install_host_desktop() {
  # shellcheck source=/dev/null
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/nexus-host-desktop-install.sh" ]] && \
    source "${NEXUS_INSTALL_ROOT}/lib/nexus-host-desktop-install.sh"
  declare -f nexus_host_desktop_install_run >/dev/null 2>&1 && \
    nexus_host_desktop_install_run 2>/dev/null || true
}