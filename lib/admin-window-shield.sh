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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/admin-window-shield.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Admin window shield — interdict keyboard hooks and capture tools near operator admin UI.

nexus_admin_window_shield_enabled() {
  [[ "${NEXUS_ADMIN_WINDOW_SHIELD:-1}" == "1" ]]
}

nexus_admin_window_shield_once() {
  nexus_admin_window_shield_enabled || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/admin-window-shield.py"
  [[ -f "$py" ]] || return 0
  local pythong_bin="${NEXUS_PYTHONG:-$(nexus_resolve_pythong 2>/dev/null || true)}"
  [[ -n "$pythong_bin" ]] || return 0
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
    "$pythong_bin" "$py" enforce >/dev/null 2>&1 || true
}

nexus_admin_window_shield_loop() {
  nexus_admin_window_shield_enabled || return 0
  while true; do
    nexus_admin_window_shield_once
    if declare -f nexus_field_loop_wait >/dev/null 2>&1; then
      nexus_field_loop_wait "${NEXUS_ADMIN_SHIELD_INTERVAL:-5}" "${NEXUS_STATE_DIR}"
    else
      local interval="${NEXUS_ADMIN_SHIELD_INTERVAL:-5}"
      nexus_await_seconds "$interval" "${NEXUS_STATE_DIR}" 2>/dev/null || sleep "$interval"
    fi
  done
}