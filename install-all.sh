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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:install-all.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# System install only — daily use: ./nexus.sh (NEXUS Field OS launcher).
# NEXUS Field — system install via NXF manifest (one admin approval).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
export SG_ROOT="${SG_ROOT:-${ROOT}}"
export NEXUS_INSTALL_SRC="${ROOT}"

exec bash "${ROOT}/lib/nxf-install.sh" --mode system "$@"