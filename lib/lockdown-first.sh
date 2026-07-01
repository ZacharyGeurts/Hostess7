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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/lockdown-first.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# First-run lockdown — block live public peers until operator trusts recommended ones.

nexus_lockdown_first_apply() {
  [[ "${NEXUS_LOCKDOWN_FIRST:-1}" == "1" ]] || return 0
  local marker="${NEXUS_STATE_DIR}/lockdown-first.done"
  [[ -f "$marker" ]] && return 0

  declare -f nexus_firewall_block_ip >/dev/null 2>&1 || return 0
  declare -f nexus_firewall_is_sacred_ip >/dev/null 2>&1 || return 0
  declare -f nexus_firewall_is_trusted >/dev/null 2>&1 && nexus_firewall_trust_init

  local cataloged=0 line rip rport proc
  while IFS= read -r line; do
    [[ "$line" =~ ESTAB ]] || continue
    rip="$(sed -n 's/.*[[:space:]]\([0-9]\{1,3\}\(\.[0-9]\{1,3\}\)\{3\}\):[0-9]\+[[:space:]].*/\1/p' <<<"$line" | tail -1)"
    rport="$(sed -n 's/.*[[:space:]][0-9.]*:\([0-9]\+\)[[:space:]].*/\1/p' <<<"$line" | tail -1)"
    proc="$(sed -n 's/.*users:((\"\([^\"]*\)\".*/\1/p' <<<"$line")"
    [[ -n "$rip" ]] || continue
    [[ "$rip" =~ ^127\. ]] && continue
    nexus_firewall_is_private_ip "$rip" 2>/dev/null && continue
    cataloged=$((cataloged + 1))
    if declare -f nexus_firewall_permit_flow >/dev/null 2>&1 \
      && [[ "$rport" =~ ^[0-9]+$ && "$rport" -gt 0 ]]; then
      nexus_firewall_is_sacred_ip "$rip" 2>/dev/null && continue
      if declare -f nexus_firewall_is_trusted >/dev/null 2>&1; then
        nexus_firewall_is_trusted "$rip" both 2>/dev/null && continue
      fi
      nexus_firewall_permit_flow out "$rip" "$rport" "${NEXUS_FIREWALL_PERMIT_FLOW_DURATION:-7200}" "lockdown-first-catalog" || true
    fi
  done < <(ss -H -tan state established 2>/dev/null | head -n 120)

  printf 'applied=packet-permission\ncataloged=%s\nts=%s\n' "$cataloged" "$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)" >"$marker"
  chmod 640 "$marker" 2>/dev/null || true
  nexus_log "INFO" "lockdown-first" "LOCKDOWN_FIRST v4.0 cataloged=${cataloged} flows — packet permission blocks harmful sections only"
  return 0
}