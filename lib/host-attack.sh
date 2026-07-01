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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/host-attack.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS Host Attack Map — global threat globe for the panel.

nexus_host_attack_publish() {
  [[ "${NEXUS_HOST_ATTACK_MAP:-1}" == "1" ]] || return 0
  command -v pythong >/dev/null 2>&1 || return 0
  local script="${NEXUS_INSTALL_ROOT}/lib/host-attack-map.py"
  [[ -f "$script" ]] || return 0
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" NEXUS_HOST_ATTACK_FAST=1 \
    pythong "$script" build-fast >/dev/null 2>&1 || true
}

nexus_host_attack_publish_deep() {
  [[ "${NEXUS_HOST_ATTACK_MAP:-1}" == "1" ]] || return 0
  command -v pythong >/dev/null 2>&1 || return 0
  local script="${NEXUS_INSTALL_ROOT}/lib/host-attack-map.py"
  [[ -f "$script" ]] || return 0
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$script" build >/dev/null 2>&1 || true
}

nexus_host_attacks_panel_json() {
  command -v pythong >/dev/null 2>&1 || { printf '{"points":[],"stats":{"total":0}}'; return 0; }
  local script="${NEXUS_INSTALL_ROOT}/lib/host-attack-map.py"
  [[ -f "$script" ]] || { printf '{"points":[],"stats":{"total":0}}'; return 0; }
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$script" json-panel 2>/dev/null || printf '{"points":[],"stats":{"total":0}}'
}

nexus_host_attacks_json() {
  command -v pythong >/dev/null 2>&1 || { printf '{}'; return 0; }
  local script="${NEXUS_INSTALL_ROOT}/lib/host-attack-map.py"
  [[ -f "$script" ]] || { printf '{}'; return 0; }
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    pythong "$script" json 2>/dev/null || printf '{}'
}