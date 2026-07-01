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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/planetary-observer.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Planetary observation + proactive kills — global sight, certainty-gated destroy.

nexus_planetary_observer_json() {
  local py="${NEXUS_INSTALL_ROOT}/lib/planetary-observer.py"
  [[ -f "$py" ]] || { printf '{}'; return 0; }
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$py" json 2>/dev/null || printf '{}'
}

nexus_planetary_observer_cycle() {
  [[ "${NEXUS_PLANETARY_OBSERVER:-1}" == "1" ]] || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/planetary-observer.py"
  [[ -f "$py" ]] || return 0
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$py" cycle >/dev/null 2>&1 || true
}

nexus_planetary_observer_proactive() {
  [[ "${NEXUS_PLANETARY_PROACTIVE_KILL:-1}" == "1" ]] || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/planetary-observer.py"
  [[ -f "$py" ]] || return 0
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$py" proactive 2>/dev/null || true
}