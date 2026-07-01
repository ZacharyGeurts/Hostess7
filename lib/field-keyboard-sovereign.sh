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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-keyboard-sovereign.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# C2 keyboard sovereignty — engage on front-hook board, release on panel shutdown/kill.

nexus_keyboard_sovereign_enabled() {
  [[ "${NEXUS_KEYBOARD_SOVEREIGN:-1}" == "1" ]]
}

nexus_keyboard_sovereign_engage() {
  nexus_keyboard_sovereign_enabled || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/field-keyboard-sovereign.py"
  [[ -f "$py" ]] || return 0
  local runner="${NEXUS_PYTHONG:-pythong}"
  command -v "$runner" >/dev/null 2>&1 || runner="python3"
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    DISPLAY="${DISPLAY:-:0}" \
    "$runner" "$py" engage >/dev/null 2>&1 || true
  nexus_log "INFO" "keyboard-sovereign" "ENGAGE display=${DISPLAY:-:0}"
}

nexus_keyboard_sovereign_release() {
  local py="${NEXUS_INSTALL_ROOT}/lib/field-keyboard-sovereign.py"
  [[ -f "$py" ]] || return 0
  local runner="${NEXUS_PYTHONG:-pythong}"
  command -v "$runner" >/dev/null 2>&1 || runner="python3"
  local reason="${1:-shutdown}"
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
    DISPLAY="${DISPLAY:-:0}" \
    "$runner" "$py" release "$reason" >/dev/null 2>&1 || true
  nexus_log "INFO" "keyboard-sovereign" "RELEASE reason=${reason}"
}