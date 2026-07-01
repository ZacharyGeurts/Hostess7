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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/home-protector.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Immediate Home Protector — 3-bedroom home airspace publish helpers.

nexus_home_protector_publish() {
  [[ "${NEXUS_HOME_PROTECTOR:-1}" == "1" ]] || return 0
  command -v pythong >/dev/null 2>&1 || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/home-protector.py"
  [[ -f "$py" ]] || return 0
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$py" build >/dev/null 2>&1 || true
}

nexus_home_protector_json() {
  if declare -f nexus_home_protector_publish >/dev/null 2>&1; then
    nexus_home_protector_publish
  fi
  local py="${NEXUS_INSTALL_ROOT}/lib/home-protector.py"
  local cache="${NEXUS_STATE_DIR}/home-protector-panel.json"
  if [[ -f "$py" ]]; then
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      pythong "$py" json 2>/dev/null && return 0
  fi
  if [[ -s "$cache" ]]; then
    pythong -c "import json,sys; json.dump(json.load(open(sys.argv[1])), sys.stdout)" "$cache" 2>/dev/null
    return 0
  fi
  printf '{"schema":"home-protector/v1","stats":{"total":0},"entities":[],"table":[]}'
}