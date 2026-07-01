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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/self-access.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS self-access — never lock the operator out of localhost / panel / DNS.

nexus_firewall_ensure_self_access() {
  declare -f nexus_firewall_unblock_ip >/dev/null 2>&1 || return 0
  declare -f nexus_firewall_authorize_ip >/dev/null 2>&1 || return 0

  local ip
  for ip in 127.0.0.1 127.0.0.0; do
    nexus_firewall_unblock_ip out "$ip" 2>/dev/null || true
    nexus_firewall_unblock_ip in "$ip" 2>/dev/null || true
  done

  nexus_firewall_authorize_ip 127.0.0.1 both "nexus-panel-localhost" "self-access" 2>/dev/null || true

  if declare -f nexus_firewall_temp_allow_ip >/dev/null 2>&1; then
    nexus_firewall_temp_allow_ip out 127.0.0.1 3153600000 2>/dev/null || true
  fi

  nexus_log "INFO" "self-access" "SELF_ACCESS ensured localhost+panel never blocked"
  return 0
}

nexus_firewall_refuse_block_self() {
  local ip="${1:-}"
  [[ -z "$ip" ]] && return 1
  [[ "$ip" =~ ^127\. ]] && return 0
  [[ "$ip" == "0.0.0.0" ]] && return 0
  if declare -f nexus_firewall_is_sacred_ip >/dev/null 2>&1 && nexus_firewall_is_sacred_ip "$ip"; then
    return 0
  fi
  return 1
}