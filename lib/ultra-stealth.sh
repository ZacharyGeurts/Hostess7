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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/ultra-stealth.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Ultra-stealth — cgroup budget, adaptive event-driven pacing, <5% CPU target.

NEXUS_CPU_QUOTA_PCT="${NEXUS_CPU_QUOTA_PCT:-5}"
NEXUS_AWAIT_MAX_SEC="${NEXUS_AWAIT_MAX_SEC:-5}"
NEXUS_BEHAVIOR_POLL_CALM="${NEXUS_BEHAVIOR_POLL_CALM:-5}"
NEXUS_BEHAVIOR_POLL_ALERT="${NEXUS_BEHAVIOR_POLL_ALERT:-5}"
NEXUS_BEHAVIOR_POLL_STORM="${NEXUS_BEHAVIOR_POLL_STORM:-2}"
NEXUS_PRIVACY_POLL_CALM="${NEXUS_PRIVACY_POLL_CALM:-5}"
NEXUS_PRIVACY_POLL_ALERT="${NEXUS_PRIVACY_POLL_ALERT:-5}"
NEXUS_PRIVACY_POLL_STORM="${NEXUS_PRIVACY_POLL_STORM:-5}"
NEXUS_PACKET_POLL_CALM="${NEXUS_PACKET_POLL_CALM:-5}"
NEXUS_PACKET_POLL_ALERT="${NEXUS_PACKET_POLL_ALERT:-5}"
NEXUS_PACKET_POLL_STORM="${NEXUS_PACKET_POLL_STORM:-3}"
NEXUS_VIGIL_MAINTAIN_INTERVAL="${NEXUS_VIGIL_MAINTAIN_INTERVAL:-5}"

nexus_ultra_stealth_enabled() {
  if declare -f nexus_field_max_enabled >/dev/null 2>&1 && nexus_field_max_enabled; then
    return 1
  fi
  [[ "${NEXUS_ULTRA_STEALTH:-1}" == "1" ]]
}

nexus_apply_cgroup_self() {
  if declare -f nexus_field_max_enabled >/dev/null 2>&1 && nexus_field_max_enabled; then
    return 0
  fi
  nexus_ultra_stealth_enabled || return 0
  if [[ -w /sys/fs/cgroup/cgroup.controllers ]]; then
    local slice="nexus-shield.slice"
    mkdir -p "/sys/fs/cgroup/${slice}" 2>/dev/null || true
    echo "$$" >"/sys/fs/cgroup/${slice}/cgroup.procs" 2>/dev/null || true
    echo "50000 ${NEXUS_CPU_QUOTA_PCT}000" >"/sys/fs/cgroup/${slice}/cpu.max" 2>/dev/null || true
  fi
  nexus_low_priority
}

nexus_adaptive_poll_interval() {
  local module="${1:-behavior}"
  if declare -f nexus_field_max_enabled >/dev/null 2>&1 && nexus_field_max_enabled; then
    nexus_await_clamp "${NEXUS_FIELD_LOOP_SEC:-2}"
    return 0
  fi
  local mode raw
  mode="$(nexus_vigil_get_mode 2>/dev/null || echo calm)"
  case "$module" in
    behavior)
      case "$mode" in
        storm) raw="$NEXUS_BEHAVIOR_POLL_STORM" ;;
        alert) raw="$NEXUS_BEHAVIOR_POLL_ALERT" ;;
        *) raw="$NEXUS_BEHAVIOR_POLL_CALM" ;;
      esac
      ;;
    privacy)
      case "$mode" in
        storm) raw="$NEXUS_PRIVACY_POLL_STORM" ;;
        alert) raw="$NEXUS_PRIVACY_POLL_ALERT" ;;
        *) raw="$NEXUS_PRIVACY_POLL_CALM" ;;
      esac
      ;;
    packet)
      case "$mode" in
        storm) raw="$NEXUS_PACKET_POLL_STORM" ;;
        alert) raw="$NEXUS_PACKET_POLL_ALERT" ;;
        *) raw="$NEXUS_PACKET_POLL_CALM" ;;
      esac
      ;;
    *)
      raw="$NEXUS_VIGIL_MAINTAIN_INTERVAL"
      ;;
  esac
  nexus_await_clamp "${raw:-5}"
}

nexus_cpu_budget_ok() {
  local usage
  usage="$(awk '{print int($2)}' /proc/self/stat 2>/dev/null || echo 0)"
  [[ "${usage:-0}" -lt 95 ]]
}
