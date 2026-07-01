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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/nexus-pkexec-bridge.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# NEXUS Field pkexec bridge — sole polkit entry; whitelisted verbs only; audit trail.
set -euo pipefail

_BRIDGE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}"
AUDIT_LOG="${STATE_DIR}/pkexec-audit.jsonl"

_VERBS=(run-install run-update run-harden run-service run-underlay run-znetwork run-freeze)

nexus_pkexec_audit() {
  local event="$1" detail="${2:-}"
  mkdir -p "$STATE_DIR" 2>/dev/null || true
  printf '{"ts":"%s","event":"%s","verb":"%s","pkexec_uid":"%s","pkexec_user":"%s","pid":%s,"detail":%s}\n' \
    "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$event" "${VERB:-}" "${PKEXEC_UID:-}" "${PKEXEC_USER:-}" "$$" \
    "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$detail" 2>/dev/null || echo '""')" \
    >>"$AUDIT_LOG" 2>/dev/null || true
}

nexus_pkexec_scrub_env() {
  unset LD_PRELOAD LD_AUDIT LD_LIBRARY_PATH BASH_ENV ENV PERL5LIB RUBYLIB PYTHONPATH
  unset SUDO_COMMAND SUDO_UID SUDO_GID
  export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
  umask 022
}

nexus_pkexec_allowed_root() {
  local target="$1"
  local real
  real="$(readlink -f "$target" 2>/dev/null || true)"
  [[ -n "$real" ]] || return 1
  local roots=(
    "$INSTALL_ROOT"
    "${SG_ROOT:-}/NewLatest"
    "${SG_ROOT:-}"
    "/usr/local/lib/nexus-shield"
  )
  local r
  for r in "${roots[@]}"; do
    [[ -n "$r" ]] || continue
    r="$(readlink -f "$r" 2>/dev/null || true)"
    [[ -n "$r" ]] || continue
    [[ "$real" == "$r" || "$real" == "$r"/* ]] && return 0
  done
  return 1
}

nexus_pkexec_require_root() {
  if [[ "$(id -u)" -ne 0 ]]; then
    nexus_pkexec_audit "deny_not_root" "expected uid 0 after pkexec"
    echo "nexus-pkexec-bridge: not root — elevation failed." >&2
    exit 1
  fi
  if [[ -z "${PKEXEC_UID:-}" ]]; then
    nexus_pkexec_audit "deny_no_pkexec" "PKEXEC_UID unset — direct invocation blocked"
    echo "nexus-pkexec-bridge: must be invoked via pkexec." >&2
    exit 1
  fi
}

nexus_pkexec_run_install() {
  local script="${1:-}"
  shift || true
  [[ -n "$script" && -f "$script" ]] || {
    nexus_pkexec_audit "deny_missing_script" "$script"
    exit 2
  }
  nexus_pkexec_allowed_root "$script" || {
    nexus_pkexec_audit "deny_path" "$script"
    echo "nexus-pkexec-bridge: script outside allowed roots." >&2
    exit 2
  }
  local base
  base="$(basename "$script")"
  case "$base" in
    install-all.sh|genius_shield.sh|install.sh|stealth_install.sh) ;;
    *)
      nexus_pkexec_audit "deny_script_name" "$base"
      echo "nexus-pkexec-bridge: installer script not whitelisted." >&2
      exit 2
      ;;
  esac
  export NEXUS_ELEVATED_ROOT=1
  export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-/usr/local/lib/nexus-shield}"
  export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}"
  nexus_pkexec_audit "allow" "$script"
  exec bash "$script" "$@"
}

nexus_pkexec_run_update() {
  local target="${1:-}"
  [[ -n "$target" && -f "$target" ]] || {
    nexus_pkexec_audit "deny_empty_update" "$target"
    exit 2
  }
  nexus_pkexec_allowed_root "$target" || {
    nexus_pkexec_audit "deny_update_path" "$target"
    exit 2
  }
  case "$(basename "$target")" in
    nexus-update-apply.sh) ;;
    update-elevate-inner.sh)
      local real_state
      real_state="$(readlink -f "$STATE_DIR" 2>/dev/null || true)"
      [[ -n "$real_state" && "$target" == "$real_state/"* ]] || {
        nexus_pkexec_audit "deny_update_inner_path" "$target"
        exit 2
      }
      ;;
    *)
      nexus_pkexec_audit "deny_update_script" "$target"
      exit 2
      ;;
  esac
  export NEXUS_ELEVATED_ROOT=1
  nexus_pkexec_audit "allow" "$target"
  exec bash "$target"
}

nexus_pkexec_run_harden() {
  local py="${INSTALL_ROOT}/lib/cpu-vulnerability-shield.py"
  [[ -f "$py" ]] || py="${_BRIDGE}/cpu-vulnerability-shield.py"
  [[ -f "$py" ]] || {
    nexus_pkexec_audit "deny_harden_missing" "$py"
    exit 2
  }
  export NEXUS_ELEVATED_ROOT=1 NEXUS_CPU_VULN_APPLY=1
  nexus_pkexec_audit "allow" "$py"
  exec python3 "$py" board
}

nexus_pkexec_run_service() {
  local cmd="${1:-status}"
  case "$cmd" in
    restart|start|stop|status|reload) ;;
    *)
      nexus_pkexec_audit "deny_service_cmd" "$cmd"
      exit 2
      ;;
  esac
  nexus_pkexec_audit "allow" "nexus-genius:$cmd"
  exec systemctl "$cmd" nexus-genius.service
}

nexus_pkexec_run_znetwork() {
  local marker="${1:-}"
  [[ -n "$marker" && -f "$marker" ]] || {
    nexus_pkexec_audit "deny_znetwork_marker" "$marker"
    exit 2
  }
  local real_state
  real_state="$(readlink -f "$STATE_DIR" 2>/dev/null || true)"
  [[ -n "$real_state" && "$marker" == "$real_state/"* ]] || {
    nexus_pkexec_audit "deny_znetwork_marker_path" "$marker"
    exit 2
  }
  export NEXUS_ELEVATED_ROOT=1
  nexus_pkexec_audit "allow" "znetwork:elevation_sealed"
  touch "$marker"
  exit 0
}

nexus_pkexec_run_freeze() {
  local cmd="${1:-}"
  shift || true
  case "$cmd" in
    prepare|freeze|thaw|close|resume-witness|json) ;;
    *)
      nexus_pkexec_audit "deny_freeze_cmd" "$cmd"
      echo "nexus-pkexec-bridge: freeze verb not whitelisted." >&2
      exit 2
      ;;
  esac
  local py="${INSTALL_ROOT}/lib/field-host-freeze.py"
  [[ -f "$py" ]] || py="${_BRIDGE}/field-host-freeze.py"
  [[ -f "$py" ]] || {
    nexus_pkexec_audit "deny_freeze_missing" "$py"
    exit 2
  }
  export NEXUS_ELEVATED_ROOT=1
  nexus_pkexec_audit "allow" "freeze:$cmd"
  local -a args=(python3 "$py" "$cmd" --elevated)
  local arg
  for arg in "$@"; do
    args+=("$arg")
  done
  exec "${args[@]}"
}

nexus_pkexec_run_underlay() {
  local cmd="${1:-}"
  shift || true
  case "$cmd" in
    commit|wrdt-apply|reboot|grok-prep|json) ;;
    *)
      nexus_pkexec_audit "deny_underlay_cmd" "$cmd"
      echo "nexus-pkexec-bridge: underlay verb not whitelisted." >&2
      exit 2
      ;;
  esac
  local py="${INSTALL_ROOT}/lib/field-underlay-switch.py"
  [[ -f "$py" ]] || {
    nexus_pkexec_audit "deny_underlay_missing" "$py"
    exit 2
  }
  export NEXUS_ELEVATED_ROOT=1
  nexus_pkexec_audit "allow" "underlay:$cmd"
  local -a args=(python3 "$py" "$cmd" --elevated)
  local arg
  for arg in "$@"; do
    [[ "$arg" == "--confirm" ]] && args+=(--confirm)
  done
  exec "${args[@]}"
}

VERB="${1:-}"
shift || true
nexus_pkexec_scrub_env
nexus_pkexec_require_root

case "$VERB" in
  run-install) nexus_pkexec_run_install "$@" ;;
  run-update)  nexus_pkexec_run_update "$@" ;;
  run-harden)  nexus_pkexec_run_harden "$@" ;;
  run-service) nexus_pkexec_run_service "$@" ;;
  run-underlay) nexus_pkexec_run_underlay "$@" ;;
  run-freeze)   nexus_pkexec_run_freeze "$@" ;;
  run-znetwork) nexus_pkexec_run_znetwork "$@" ;;
  *)
    nexus_pkexec_audit "deny_verb" "$VERB"
    echo "nexus-pkexec-bridge: unknown verb '${VERB}'." >&2
    exit 2
    ;;
esac