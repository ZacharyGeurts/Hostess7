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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/panel-i18n.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Panel i18n — language preference JSON for threat panel.

nexus_panel_language_json() {
  local script="${NEXUS_INSTALL_ROOT}/lib/panel-i18n.py"
  if [[ ! -f "$script" ]]; then
    printf '{"schema":"panel-language/v1","active":{"code":"en-US","source":"default"},"languages":[],"messages":{}}'
    return 0
  fi
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
    NEXUS_I18N_DIR="${NEXUS_I18N_DIR:-${NEXUS_INSTALL_ROOT}/data/i18n}" \
    pythong "$script" json 2>/dev/null \
    || printf '{"schema":"panel-language/v1","active":{"code":"en-US","source":"default"},"languages":[],"messages":{}}'
}