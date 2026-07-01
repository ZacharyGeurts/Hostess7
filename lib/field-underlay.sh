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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-underlay.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Field underlay — board drop-in replacement posture (guest inside protections).
set -euo pipefail

nexus_field_underlay_board() {
  [[ "${NEXUS_FIELD_UNDERLAY:-1}" == "1" ]] || return 0
  local root="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  local py="${root}/lib/field-underlay.py"
  [[ -f "$py" ]] || return 0
  NEXUS_INSTALL_ROOT="${root}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}" \
    SG_ROOT="${SG_ROOT:-}" KILROY_ROOT="${KILROY_ROOT:-}" QUEEN_ROOT="${QUEEN_ROOT:-}" \
    pythong "$py" board 2>/dev/null || pythong "$py" json >/dev/null || true
  # Early boot: unified field + front hook only — skip heavy Tristate scan before guest OS.
  [[ "${NEXUS_FIELD_EARLY_BOOT_LAYER:-}" == "1" ]] && return 0
  if [[ -f "${root}/lib/field-underlay-switch.sh" ]]; then
    # shellcheck source=/dev/null
    source "${root}/lib/field-underlay-switch.sh"
    nexus_underlay_switch_board
    [[ "${NEXUS_UNDERLAY_HOTKEY:-1}" == "1" ]] && nexus_underlay_hotkey_install "${SUDO_USER:-$USER}" 2>/dev/null || true
  fi
}