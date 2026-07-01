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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-drive-system.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Field Drive System — whole NEXUS on TEAM fieldstorage; minimal browser talk path.

# shellcheck source=/dev/null
[[ -f "$(dirname "${BASH_SOURCE[0]}")/sg-paths.sh" ]] && source "$(dirname "${BASH_SOURCE[0]}")/sg-paths.sh"
sg_paths_export_defaults 2>/dev/null || true
HOSTESS7_TEAM_FIELD="${HOSTESS7_TEAM_FIELD:-$(sg_paths_hostess7_team_field 2>/dev/null)}"
HOSTESS7_ROOT="${HOSTESS7_ROOT:-$(sg_paths_hostess7_root 2>/dev/null)}"

nexus_field_drive_root() {
  local local_mirror="${NEXUS_INSTALL_ROOT:-.}/.nexus-field-drive"
  local lock="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}/field-underlay-lock.json"
  # Pre-commit: host mirror only — no field files on TEAM/KILROY drives.
  if [[ ! -f "$lock" ]] || ! grep -q '"committed"[[:space:]]*:[[:space:]]*true' "$lock" 2>/dev/null; then
    mkdir -p "${local_mirror}/nexus-field/state" 2>/dev/null || true
    printf '%s\n' "${local_mirror}"
    return 0
  fi
  if [[ -d "${local_mirror}/nexus-field/state" ]]; then
    printf '%s\n' "${local_mirror}"
    return 0
  fi
  if [[ -d "${HOSTESS7_TEAM_FIELD}/nexus-field" ]]; then
    printf '%s\n' "${HOSTESS7_TEAM_FIELD}"
    return 0
  fi
  if [[ -d "${HOSTESS7_TEAM_FIELD}/brain" ]]; then
    printf '%s\n' "${HOSTESS7_TEAM_FIELD}"
    return 0
  fi
  printf '%s\n' "${local_mirror}"
}

nexus_field_drive_apply_paths() {
  [[ "${NEXUS_FIELD_DRIVE:-1}" == "1" ]] || return 0
  # Never redirect runtime state to drive until underlay commit (no field-in-field).
  if [[ "${NEXUS_FIELD_DRIVE_STATE_REDIRECT:-0}" != "1" ]]; then
    local lock="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}/field-underlay-lock.json"
    if [[ ! -f "$lock" ]] || ! grep -q '"committed"[[:space:]]*:[[:space:]]*true' "$lock" 2>/dev/null; then
      return 0
    fi
  fi
  local root field_base state_on_drive
  root="$(nexus_field_drive_root 2>/dev/null)" || return 0
  field_base="${root}/nexus-field"
  state_on_drive="${field_base}/state"
  [[ -d "$state_on_drive" ]] || return 0
  [[ -f "${field_base}/active.json" || -f "${field_base}/manifest.json" ]] || return 0

  export NEXUS_HOST_STATE_DIR="${NEXUS_HOST_STATE_DIR:-/var/lib/nexus-shield}"
  export NEXUS_FIELD_DRIVE_ACTIVE=1
  export NEXUS_FIELD_DRIVE_ROOT="$field_base"
  export NEXUS_FIELD_DRIVE_STATE="$state_on_drive"
  export NEXUS_STATE_DIR="$state_on_drive"
  export NEXUS_SHADOW_DIR="${NEXUS_STATE_DIR}/shadow"
  export NEXUS_BEHAVIOR_DIR="${NEXUS_STATE_DIR}/behavior"
  export NEXUS_VIGIL_STATE="${NEXUS_STATE_DIR}/vigil.state"

  mkdir -p "$NEXUS_STATE_DIR" "$NEXUS_SHADOW_DIR" "$NEXUS_BEHAVIOR_DIR" \
    "${field_base}/talk/inbox" "${field_base}/talk/outbox" "${field_base}/run" 2>/dev/null || true
  return 0
}

nexus_field_drive_publish() {
  [[ "${NEXUS_FIELD_DRIVE:-1}" == "1" ]] || return 0
  command -v pythong >/dev/null 2>&1 || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/field-drive-system.py"
  [[ -f "$py" ]] || return 0
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}" \
    NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    HOSTESS7_TEAM_FIELD="$HOSTESS7_TEAM_FIELD" \
    HOSTESS7_ROOT="$HOSTESS7_ROOT" \
    pythong "$py" sync >/dev/null 2>&1 || true
}

nexus_field_drive_publish_full() {
  [[ "${NEXUS_FIELD_DRIVE:-1}" == "1" ]] || return 0
  command -v pythong >/dev/null 2>&1 || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/field-drive-system.py"
  [[ -f "$py" ]] || return 0
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}" \
    NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    HOSTESS7_TEAM_FIELD="$HOSTESS7_TEAM_FIELD" \
    HOSTESS7_ROOT="$HOSTESS7_ROOT" \
    pythong "$py" publish >/dev/null 2>&1 || true
}

nexus_field_drive_json() {
  if declare -f nexus_field_drive_publish >/dev/null 2>&1; then
    nexus_field_drive_publish
  fi
  local py="${NEXUS_INSTALL_ROOT}/lib/field-drive-system.py"
  if [[ -f "$py" ]]; then
    NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}" \
      NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
      HOSTESS7_TEAM_FIELD="$HOSTESS7_TEAM_FIELD" \
      HOSTESS7_ROOT="$HOSTESS7_ROOT" \
      pythong "$py" json 2>/dev/null && return 0
  fi
  printf '{"schema":"field-drive-system/v1","drive_mounted":false,"whole_system_on_drive":false,"drives":[],"gui_on_drive":false,"panel_url":"/field"}'
}

nexus_field_drive_inbox_loop() {
  [[ "${NEXUS_FIELD_DRIVE:-1}" == "1" ]] || return 0
  command -v pythong >/dev/null 2>&1 || return 0
  local py="${NEXUS_INSTALL_ROOT}/lib/field-drive-system.py"
  [[ -f "$py" ]] || return 0
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}" \
    NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    HOSTESS7_TEAM_FIELD="$HOSTESS7_TEAM_FIELD" \
    pythong "$py" inbox >/dev/null 2>&1 || true
}