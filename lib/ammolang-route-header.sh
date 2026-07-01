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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/ammolang-route-header.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Drop-in header: AML_TASK must be set before sourcing.
#   AML_TASK=stack_start
#   source "$(dirname "$0")/../lib/ammolang-route-header.sh"
if [[ -z "${AML_TASK:-}" ]]; then
  echo "ammolang-route-header: AML_TASK not set" >&2
  exit 1
fi
if [[ "${AML_IMPL:-}" == "1" ]]; then
  return 0 2>/dev/null || true
fi
_ROUTE_LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${_ROUTE_LIB}/ammolang-route.sh" "${AML_TASK}" "$@"