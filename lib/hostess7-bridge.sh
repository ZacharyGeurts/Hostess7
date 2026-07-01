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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/hostess7-bridge.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Hostess7 bridge — optional truth corroboration (94% noise / 6% signal filter).

# shellcheck source=/dev/null
[[ -f "${NEXUS_INSTALL_ROOT:-}/lib/sg-paths.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/sg-paths.sh"
[[ -f "$(dirname "${BASH_SOURCE[0]}")/sg-paths.sh" ]] && source "$(dirname "${BASH_SOURCE[0]}")/sg-paths.sh"
sg_paths_export_defaults 2>/dev/null || true
HOSTESS7_ROOT="${HOSTESS7_ROOT:-$(sg_paths_hostess7_root 2>/dev/null)}"

nexus_hostess7_available() {
  [[ "${NEXUS_HOSTESS7_CORROBORATE:-0}" == "1" ]] \
    && [[ -x "${HOSTESS7_ROOT}/Hostess7.sh" ]]
}

nexus_hostess7_corroborate_integrity() {
  nexus_hostess7_available || return 0
  local manifest_hash
  manifest_hash="$(sha256sum "${NEXUS_MANIFEST}" 2>/dev/null | awk '{print $1}')"
  [[ -n "$manifest_hash" ]] || return 1
  local out
  out="$(
    cd "${HOSTESS7_ROOT}" && ./Hostess7.sh truth \
      "NEXUS-Shield manifest ${manifest_hash:0:16} integrity corroboration" 2>/dev/null | tail -n 5
  )" || return 1
  [[ -n "$out" ]] || return 1
  nexus_log "INFO" "hostess7-bridge" "CORROBORATED ${out:0:120}"
  return 0
}