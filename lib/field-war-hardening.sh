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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-war-hardening.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# NEXUS C2 war machine hardening — layer chain, forever RE-KILL, full defense arm.
set -euo pipefail
export AML_BUILD=0

_LIB="$(cd "$(dirname "$0")" && pwd)"
_ROOT="$(cd "${_LIB}/.." && pwd)"

# shellcheck source=/dev/null
[[ -f "${_LIB}/nexus-common.sh" ]] && source "${_LIB}/nexus-common.sh" 2>/dev/null || true
nexus_init_runtime_paths 2>/dev/null || true

export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-${_ROOT}}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${NEXUS_INSTALL_ROOT}/.nexus-state}"
export SG_ROOT="${SG_ROOT:-$(cd "${NEXUS_INSTALL_ROOT}/.." && pwd)}"

nexus_field_war_export_env() {
  export NEXUS_WAR_MACHINE="${NEXUS_WAR_MACHINE:-1}"
  export NEXUS_C2_WAR_POSTURE="${NEXUS_C2_WAR_POSTURE:-1}"
  export NEXUS_C2_KIOSK="${NEXUS_C2_KIOSK:-0}"
  export NEXUS_EVERY_KILL_REKILL="${NEXUS_EVERY_KILL_REKILL:-1}"
  export NEXUS_BOOT_REKILL="${NEXUS_BOOT_REKILL:-1}"
  export ZOCR_REKILL_AT_BOOT="${ZOCR_REKILL_AT_BOOT:-1}"
  export NEXUS_FIELD_ATTACK_KIT="${NEXUS_FIELD_ATTACK_KIT:-1}"
  export NEXUS_FIELD_AUTO_REKILL="${NEXUS_FIELD_AUTO_REKILL:-1}"
  export NEXUS_ATTACK_KIT_AUTO_CRUSH="${NEXUS_ATTACK_KIT_AUTO_CRUSH:-1}"
  export NEXUS_KILL_DETECT="${NEXUS_KILL_DETECT:-1}"
  export SG_ROOT_KILL_PREJUDICE="${SG_ROOT_KILL_PREJUDICE:-1}"
  export SG_ROOT_SOVEREIGN_KILL="${SG_ROOT_SOVEREIGN_KILL:-1}"
  export SG_ROOT_SOVEREIGN_GUARD="${SG_ROOT_SOVEREIGN_GUARD:-1}"
  export KILROY_WAR_POSTURE="${KILROY_WAR_POSTURE:-1}"
  export KILROY_PC_CORE="${KILROY_PC_CORE:-1}"
  export QUEEN_DEFENDS_WITH_NEXUS="${QUEEN_DEFENDS_WITH_NEXUS:-1}"
  export QUEEN_DEFENDS_WITH_KILROY="${QUEEN_DEFENDS_WITH_KILROY:-1}"
  export FIELD_STACK_LAYER="${FIELD_STACK_LAYER:-hardware,nexus_c2,kilroy,ammoos,queen}"
  export NEXUS_FIELD_REKILL_INTERVAL="${NEXUS_FIELD_REKILL_INTERVAL:-45}"
}

nexus_field_war_arm_settings() {
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/nexus-settings.sh" ]] || return 0
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/nexus-settings.sh"
  if declare -f nexus_settings_apply_hostess7_armed_defaults >/dev/null 2>&1; then
    nexus_settings_apply_hostess7_armed_defaults || true
    return 0
  fi
  if declare -f nexus_settings_apply_extreme_defaults >/dev/null 2>&1; then
    nexus_settings_apply_extreme_defaults || true
  fi
}

nexus_field_war_attack_kit() {
  [[ "${NEXUS_FIELD_ATTACK_KIT:-1}" == "1" ]] || return 0
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-attack-kit.sh" ]] || return 0
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/field-attack-kit.sh"
  nexus_field_attack_init 2>/dev/null || true
  nexus_field_attack_sync_from_memory 2>/dev/null || true
  nexus_field_attack_apply_registry 2>/dev/null || true
  if declare -f nexus_field_attack_boot_rekill >/dev/null 2>&1; then
    nexus_field_attack_boot_rekill 2>/dev/null || true
  fi
  if declare -f nexus_field_attack_rekill_cycle >/dev/null 2>&1; then
    nexus_field_attack_rekill_cycle 1 2>/dev/null || true
  fi
  if declare -f nexus_field_attack_autokill >/dev/null 2>&1; then
    nexus_field_attack_autokill 2>/dev/null || true
  fi
}

nexus_field_war_kilroy_arm() {
  local war="${NEXUS_INSTALL_ROOT}/GrokLab/deploy/kilroy-war-arm.sh"
  [[ -x "$war" ]] || return 0
  AML_BUILD=0 bash "$war" >>"${NEXUS_STATE_DIR}/kilroy-war-arm.log" 2>&1 || true
}

nexus_field_war_root_guard_start() {
  [[ "${SG_ROOT_SOVEREIGN_GUARD:-1}" == "1" ]] || return 0
  local guard="${NEXUS_INSTALL_ROOT}/lib/root-sovereign-guard.sh"
  [[ -f "$guard" ]] || return 0
  if pgrep -f 'queen-root-sovereign.py guard' >/dev/null 2>&1; then
    return 0
  fi
  nohup env AML_BUILD=0 SG_ROOT="$SG_ROOT" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    NEXUS_STATE_DIR="$NEXUS_STATE_DIR" QUEEN_ROOT="${QUEEN_ROOT:-${NEXUS_INSTALL_ROOT}/Queen}" \
    bash "$guard" >>"${NEXUS_STATE_DIR}/root-sovereign-guard.log" 2>&1 &
}

nexus_field_war_rekill_patrol_start() {
  [[ "${NEXUS_FIELD_AUTO_REKILL:-1}" == "1" ]] || return 0
  if pgrep -f 'field-war-hardening.sh rekill-patrol' >/dev/null 2>&1; then
    return 0
  fi
  nohup env AML_BUILD=0 NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" NEXUS_STATE_DIR="$NEXUS_STATE_DIR" \
    SG_ROOT="$SG_ROOT" NEXUS_WAR_MACHINE=1 NEXUS_EVERY_KILL_REKILL=1 NEXUS_FIELD_ATTACK_KIT=1 \
    NEXUS_FIELD_AUTO_REKILL=1 NEXUS_FIELD_REKILL_INTERVAL="${NEXUS_FIELD_REKILL_INTERVAL:-45}" \
    bash "${NEXUS_INSTALL_ROOT}/lib/field-war-hardening.sh" rekill-patrol \
    >>"${NEXUS_STATE_DIR}/rekill-patrol.log" 2>&1 &
}

nexus_field_war_rekill_patrol_loop() {
  nexus_field_war_export_env
  # shellcheck source=/dev/null
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/field-attack-kit.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/field-attack-kit.sh"
  # shellcheck source=/dev/null
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/kill-detect.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/kill-detect.sh"
  local interval="${NEXUS_FIELD_REKILL_INTERVAL:-45}"
  while true; do
    if declare -f nexus_kill_detect_execute >/dev/null 2>&1; then
      nexus_kill_detect_execute 2>/dev/null || true
    elif declare -f nexus_field_attack_rekill_cycle >/dev/null 2>&1; then
      nexus_field_attack_rekill_cycle 0 2>/dev/null || true
    fi
    sleep "$interval"
  done
}

nexus_field_war_harden() {
  [[ "${NEXUS_WAR_MACHINE:-1}" == "1" ]] || return 0
  mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true
  nexus_field_war_export_env
  nexus_field_war_arm_settings
  nexus_field_war_attack_kit
  nexus_field_war_kilroy_arm
  nexus_field_war_root_guard_start
  nexus_field_war_rekill_patrol_start
  local py
  py="$(command -v pythong 2>/dev/null || command -v python3 2>/dev/null || true)"
  if [[ -n "$py" && -f "${NEXUS_INSTALL_ROOT}/lib/field-war-hardening.py" ]]; then
    NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" NEXUS_STATE_DIR="$NEXUS_STATE_DIR" SG_ROOT="$SG_ROOT" \
      "$py" "${NEXUS_INSTALL_ROOT}/lib/field-war-hardening.py" stamp >>"${NEXUS_STATE_DIR}/war-harden.log" 2>&1 || true
  fi
  declare -f nexus_log >/dev/null 2>&1 && nexus_log "ALERT" "field-war" "WAR_MACHINE hardened — every_kill_rekill=1 layer=nexus_c2→kilroy→ammoos→queen" || true
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  case "${1:-harden}" in
    harden) nexus_field_war_harden ;;
    rekill-patrol) nexus_field_war_rekill_patrol_loop ;;
    export-env) nexus_field_war_export_env; env | grep -E '^(NEXUS_WAR|NEXUS_C2|NEXUS_EVERY|NEXUS_BOOT|NEXUS_FIELD_ATTACK|NEXUS_FIELD_AUTO|NEXUS_KILL|SG_ROOT|KILROY_WAR|FIELD_STACK)' || true ;;
    *) echo "usage: field-war-hardening.sh [harden|rekill-patrol|export-env]" >&2; exit 2 ;;
  esac
fi