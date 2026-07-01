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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/vector-scour.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS vector scour — classify active peers; populate intel cache for gatekeeper.

nexus_vector_scour_publish() {
  [[ "${NEXUS_VECTOR_INTEL:-1}" == "1" ]] || return 0
  command -v pythong >/dev/null 2>&1 || return 0
  local script="${NEXUS_INSTALL_ROOT}/lib/vector-intel.py"
  [[ -f "$script" ]] || return 0
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$script" scour >/dev/null 2>&1 || true
  if declare -f nexus_angel_dossier_publish >/dev/null 2>&1; then
    nexus_angel_dossier_publish
  elif [[ -f "${NEXUS_INSTALL_ROOT}/lib/angel-dossier.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/angel-dossier.sh"
    nexus_angel_dossier_publish
  fi
  if declare -f nexus_host_attack_publish >/dev/null 2>&1; then
    nexus_host_attack_publish
  elif [[ -f "${NEXUS_INSTALL_ROOT}/lib/host-attack.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/host-attack.sh"
    nexus_host_attack_publish
  fi
}

nexus_vector_intel_json() {
  local scour="${NEXUS_STATE_DIR}/vector-scour.json"
  if [[ -s "$scour" ]]; then
    pythong -c "import json,sys; json.dump(json.load(open(sys.argv[1])), sys.stdout)" "$scour" 2>/dev/null
  else
    printf '{"active_count":0,"pest_count":0,"active_vectors":[],"pests":[],"never_unknown":true}'
  fi
}