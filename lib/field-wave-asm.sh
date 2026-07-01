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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-wave-asm.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Field Wave ASM — build field-fast RTL-SDR USB probe (no lsusb).

[[ -f "${NEXUS_INSTALL_ROOT}/lib/nexus-common.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/nexus-common.sh"

NEXUS_FIELD_WAVE_ASM="${NEXUS_FIELD_WAVE_ASM:-${NEXUS_INSTALL_ROOT}/lib/bin/field-wave-asm}"
NEXUS_FIELD_WAVE_ASM_SRC="${NEXUS_INSTALL_ROOT}/lib/field-wave-asm.c"

nexus_field_wave_asm_build() {
  [[ "${NEXUS_FIELD_WAVE:-1}" == "1" ]] || return 0
  local g16="${GROK16_ROOT:-${SG_ROOT:-}/Grok16}/bin/g16"
  local compiler="gcc"
  local flags=(-O2 -pipe -fstack-protector-strong -D_FORTIFY_SOURCE=2 -fPIE -pie)
  if [[ -x "$g16" ]]; then
    compiler="$g16"
    flags=(-std=gnu17 -O3 -march=native -fPIE -pie)
    local gpy="${NEXUS_PYTHONG:-pythong}"
    if [[ -f "${GROK16_ROOT}/lib/g16-compile-combinatronics.py" ]] && command -v "$gpy" >/dev/null 2>&1; then
      "$gpy" "${GROK16_ROOT}/lib/g16-compile-combinatronics.py" gate >/dev/null 2>&1 || true
    fi
  elif ! command -v gcc >/dev/null 2>&1; then
    if declare -f nexus_log >/dev/null 2>&1; then
      nexus_log "WARN" "field-wave-asm" "gcc missing — sysfs Python fallback only"
    fi
    return 1
  fi
  local src="${NEXUS_FIELD_WAVE_ASM_SRC}"
  [[ -f "$src" ]] || src="${NEXUS_INSTALL_ROOT}/lib/field-wave-asm.c"
  [[ -f "$src" ]] || return 1
  local out_dir
  out_dir="$(dirname "$NEXUS_FIELD_WAVE_ASM")"
  mkdir -p "$out_dir" 2>/dev/null || true
  local err
  err="$("$compiler" "${flags[@]}" -o "$NEXUS_FIELD_WAVE_ASM" "$src" 2>&1)" || {
    if declare -f nexus_log >/dev/null 2>&1; then
      nexus_log "WARN" "field-wave-asm" "build failed: ${err}"
    fi
    return 1
  }
  chmod 755 "$NEXUS_FIELD_WAVE_ASM" 2>/dev/null || true
  if [[ -x "$g16" ]] && [[ -f "${GROK16_ROOT}/lib/g16-compile-combinatronics.py" ]]; then
    local gpy="${NEXUS_PYTHONG:-pythong}"
    command -v "$gpy" >/dev/null 2>&1 && \
      "$gpy" "${GROK16_ROOT}/lib/g16-compile-combinatronics.py" stamp "$NEXUS_FIELD_WAVE_ASM" >/dev/null 2>&1 || true
  fi
  if declare -f nexus_log >/dev/null 2>&1; then
    nexus_log "INFO" "field-wave-asm" "ASM probe built compiler=${compiler} path=${NEXUS_FIELD_WAVE_ASM}"
  fi
  return 0
}

nexus_field_wave_asm_path() {
  if [[ -x "$NEXUS_FIELD_WAVE_ASM" ]]; then
    printf '%s' "$NEXUS_FIELD_WAVE_ASM"
    return 0
  fi
  if declare -f nexus_field_wave_asm_build >/dev/null 2>&1; then
    nexus_field_wave_asm_build >/dev/null 2>&1 || true
  fi
  [[ -x "$NEXUS_FIELD_WAVE_ASM" ]] && printf '%s' "$NEXUS_FIELD_WAVE_ASM"
}