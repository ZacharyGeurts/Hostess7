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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-antenna-guard.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Field antenna destroyed — hard block; kill any straggler.
nexus_field_antenna_destroyed() { return 0; }
nexus_field_antenna_blocked() {
  pkill -9 -f 'field-antenna-orchestrator|field-antenna-catch|field-antenna-launcher' 2>/dev/null || true
  return 0
}
nexus_field_antenna_cycle() { return 0; }
nexus_field_antenna_publish() { return 0; }
nexus_field_antenna_json() {
  printf '{"schema":"field-antenna/v1","destroyed":true,"removed":true}'
}