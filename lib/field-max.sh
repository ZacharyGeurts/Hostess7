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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-max.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS Field Powered — smooth + cool; event-driven loops, workstation quota unlocked.

nexus_field_max_enabled() {
  [[ "${NEXUS_FIELD_MAX:-0}" == "1" ]]
}

nexus_field_loop_interval() {
  local fallback="${1:-5}"
  if nexus_field_max_enabled; then
    printf '%s' "${NEXUS_FIELD_LOOP_SEC:-2}"
    return 0
  fi
  printf '%s' "$fallback"
}

# Event-driven tick — inotify on state dir; no blocking sleep() in field-max mode.
nexus_field_loop_wait() {
  local interval watch
  interval="$(nexus_field_loop_interval "${1:-5}")"
  watch="${2:-${NEXUS_STATE_DIR:-/tmp}}"
  [[ -d "$watch" ]] || watch="/tmp"
  nexus_await_seconds "$interval" "$watch" 2>/dev/null || {
    nexus_field_max_enabled || sleep "$interval"
  }
}

nexus_field_cpu_wait() {
  if nexus_field_max_enabled; then
    nexus_field_loop_wait 2 "${NEXUS_STATE_DIR}"
    return 0
  fi
  sleep "${1:-15}"
}