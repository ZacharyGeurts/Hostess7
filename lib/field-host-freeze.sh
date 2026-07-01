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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-host-freeze.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Field host freeze — cgroup soft freeze, ACPI mem/disk, memory lock prep.
set -euo pipefail

_LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-${_LIB}/..}"
STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}"
FIELD_SLICE="${NEXUS_FIELD_SLICE:-nexus-field.slice}"
HOST_SLICE="${NEXUS_HOST_SLICE:-nexus-host-guest.slice}"
SHIELD_SLICE="${NEXUS_SHIELD_SLICE:-nexus-shield.slice}"
CGROUP_ROOT="/sys/fs/cgroup"

nexus_freeze_log() {
  mkdir -p "$STATE_DIR" 2>/dev/null || true
  printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || date)" "$*" >>"${STATE_DIR}/field-host-freeze.log" 2>/dev/null || true
}

nexus_freeze_cgroup_v2() {
  [[ -f "${CGROUP_ROOT}/cgroup.controllers" ]]
}

nexus_freeze_ensure_slice() {
  local slice="$1"
  mkdir -p "${CGROUP_ROOT}/${slice}" 2>/dev/null || return 1
  if [[ -w "${CGROUP_ROOT}/cgroup.subtree_control" ]]; then
    grep -q "freezer" "${CGROUP_ROOT}/${slice}/cgroup.controllers" 2>/dev/null \
      || echo "+freezer" >>"${CGROUP_ROOT}/cgroup.subtree_control" 2>/dev/null || true
  fi
}

nexus_freeze_assign_pid() {
  local pid="$1" slice="$2"
  [[ -n "$pid" && "$pid" =~ ^[0-9]+$ ]] || return 1
  nexus_freeze_ensure_slice "$slice" || return 1
  echo "$pid" >"${CGROUP_ROOT}/${slice}/cgroup.procs" 2>/dev/null || return 1
}

nexus_freeze_field_pids() {
  local name pid
  for name in nexus-genius nexus-daemon threat-panel-http queen-world; do
    pid="$(pgrep -x "$name" 2>/dev/null | head -n1 || true)"
    [[ -n "$pid" ]] && nexus_freeze_assign_pid "$pid" "$FIELD_SLICE" || true
  done
  pid="$(pgrep -f 'threat-panel-http\.py' 2>/dev/null | head -n1 || true)"
  [[ -n "$pid" ]] && nexus_freeze_assign_pid "$pid" "$FIELD_SLICE" || true
  pid="$(pgrep -f 'nexus-daemon\.sh' 2>/dev/null | head -n1 || true)"
  [[ -n "$pid" ]] && nexus_freeze_assign_pid "$pid" "$FIELD_SLICE" || true
  if [[ -w "${CGROUP_ROOT}/${SHIELD_SLICE}/cgroup.procs" ]]; then
    echo "$$" >"${CGROUP_ROOT}/${SHIELD_SLICE}/cgroup.procs" 2>/dev/null || true
  fi
}

nexus_freeze_host_assign() {
  local pid
  if [[ -d "${CGROUP_ROOT}/user.slice" ]]; then
    for pid in $(cat "${CGROUP_ROOT}/user.slice/cgroup.procs" 2>/dev/null || true); do
      [[ -n "$pid" ]] || continue
      if ! grep -q "^${pid}$" "${CGROUP_ROOT}/${FIELD_SLICE}/cgroup.procs" 2>/dev/null; then
        nexus_freeze_assign_pid "$pid" "$HOST_SLICE" 2>/dev/null || true
      fi
    done
  fi
}

nexus_freeze_set() {
  local slice="$1" val="$2"
  local freeze="${CGROUP_ROOT}/${slice}/cgroup.freeze"
  [[ -f "$freeze" ]] || return 1
  echo "$val" >"$freeze"
}

nexus_freeze_soft() {
  nexus_freeze_cgroup_v2 || {
    nexus_freeze_log "soft_freeze_skip no_cgroup_v2"
    return 1
  }
  nexus_freeze_ensure_slice "$FIELD_SLICE"
  nexus_freeze_ensure_slice "$HOST_SLICE"
  nexus_freeze_field_pids
  nexus_freeze_host_assign
  nexus_freeze_set "$HOST_SLICE" 1
  nexus_freeze_log "soft_freeze host=${HOST_SLICE} field=${FIELD_SLICE}"
}

nexus_freeze_thaw() {
  nexus_freeze_cgroup_v2 || return 1
  nexus_freeze_set "$HOST_SLICE" 0 2>/dev/null || true
  nexus_freeze_log "soft_thaw host=${HOST_SLICE}"
}

nexus_freeze_lock_memory() {
  local py="${INSTALL_ROOT}/lib/field-host-freeze.py"
  [[ -f "$py" ]] || py="${_LIB}/field-host-freeze.py"
  local runner="${NEXUS_PYTHONG:-pythong}"
  command -v "$runner" >/dev/null 2>&1 || runner="python3"
  NEXUS_INSTALL_ROOT="$INSTALL_ROOT" NEXUS_STATE_DIR="$STATE_DIR" \
    "$runner" "$py" lock-memory 2>/dev/null || true
}

nexus_freeze_acpi_mem() {
  local stamp="${STATE_DIR}/field-host-freeze.json"
  nexus_freeze_lock_memory
  nexus_freeze_log "acpi_mem_begin"
  if command -v systemd-inhibit >/dev/null 2>&1; then
    systemd-inhibit --what=sleep:shutdown:idle \
      --who="NEXUS Field" --why="host freeze mem sleep" \
      --mode=block bash -c 'echo freeze > /sys/power/state' &
    local inhibit_pid=$!
    sleep 0.5
    if ! kill -0 "$inhibit_pid" 2>/dev/null; then
      echo freeze >/sys/power/state 2>/dev/null || true
    fi
    wait "$inhibit_pid" 2>/dev/null || true
  else
    echo freeze >/sys/power/state 2>/dev/null || true
  fi
  nexus_freeze_log "acpi_mem_resume"
}

nexus_freeze_acpi_disk() {
  nexus_freeze_lock_memory
  nexus_freeze_log "acpi_disk_begin"
  echo disk >/sys/power/state 2>/dev/null || true
}

nexus_freeze_async() {
  local mode="$1"
  (
    sleep 1
    case "$mode" in
      mem) nexus_freeze_acpi_mem ;;
      disk) nexus_freeze_acpi_disk ;;
    esac
  ) &
  disown 2>/dev/null || true
}

CMD="${1:-}"
shift || true
case "$CMD" in
  ensure-slices) nexus_freeze_ensure_slice "$FIELD_SLICE"; nexus_freeze_ensure_slice "$HOST_SLICE" ;;
  soft-freeze)   nexus_freeze_soft ;;
  thaw)          nexus_freeze_thaw ;;
  lock-memory)   nexus_freeze_lock_memory ;;
  acpi-mem)      nexus_freeze_acpi_mem ;;
  acpi-disk)     nexus_freeze_acpi_disk ;;
  async-mem)     nexus_freeze_async mem ;;
  async-disk)    nexus_freeze_async disk ;;
  *)
    echo "usage: field-host-freeze.sh {ensure-slices|soft-freeze|thaw|lock-memory|acpi-mem|acpi-disk|async-mem|async-disk}" >&2
    exit 2
    ;;
esac