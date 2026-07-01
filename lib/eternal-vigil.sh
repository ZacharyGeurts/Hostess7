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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/eternal-vigil.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Eternal Vigil — adaptive watchdog thresholds (calm / alert / storm).

NEXUS_VIGIL_ALERTS="${NEXUS_VIGIL_ALERTS:-${NEXUS_STATE_DIR}/vigil-alerts.log}"

nexus_vigil_write_state() {
  local mode="$1" last_alert="${2:-0}" grp="${NEXUS_GROUP:-nexus}"
  {
    printf 'mode=%s\nlast_alert=%s\n' "$mode" "$last_alert"
  } >"$NEXUS_VIGIL_STATE"
  if [[ "$(id -u)" -eq 0 ]]; then
    chown root:"$grp" "$NEXUS_VIGIL_STATE" || nexus_log "WARN" "eternal-vigil" "vigil.state chown failed"
    chmod 640 "$NEXUS_VIGIL_STATE" || true
  else
    chmod 640 "$NEXUS_VIGIL_STATE" 2>/dev/null || true
  fi
}

nexus_vigil_fix_perms() {
  local grp="${NEXUS_GROUP:-nexus}"
  chown root:"$grp" "$NEXUS_VIGIL_ALERTS" 2>/dev/null || true
  chmod 640 "$NEXUS_VIGIL_ALERTS" 2>/dev/null || true
}

nexus_vigil_init() {
  local mode=calm last_alert=0
  nexus_ensure_dirs || return 1
  : >"$NEXUS_VIGIL_ALERTS" 2>/dev/null || touch "$NEXUS_VIGIL_ALERTS"
  if [[ -f "$NEXUS_VIGIL_STATE" ]]; then
    mode="$(grep '^mode=' "$NEXUS_VIGIL_STATE" 2>/dev/null | cut -d= -f2)"
    last_alert="$(grep '^last_alert=' "$NEXUS_VIGIL_STATE" 2>/dev/null | cut -d= -f2)"
    mode="${mode:-calm}"
    last_alert="${last_alert:-0}"
  fi
  nexus_vigil_write_state "$mode" "$last_alert"
  nexus_vigil_fix_perms
}

nexus_vigil_record_alert() {
  local module="${1:-unknown}"
  local ts
  ts="$(date +%s)"
  echo "$ts $module" >>"$NEXUS_VIGIL_ALERTS"
  nexus_vigil_fix_perms
  nexus_vigil_recompute_mode "$ts"
}

nexus_vigil_count_recent() {
  local window="${1:-600}"
  local now cutoff
  now="$(date +%s)"
  cutoff=$((now - window))
  awk -v c="$cutoff" '$1 >= c {n++} END {print n+0}' "$NEXUS_VIGIL_ALERTS" 2>/dev/null
}

nexus_vigil_compute_mode() {
  local recent last_alert now mode
  recent="$(nexus_vigil_count_recent 600)"
  last_alert="$(grep '^last_alert=' "$NEXUS_VIGIL_STATE" 2>/dev/null | cut -d= -f2)"
  now="$(date +%s)"
  mode="calm"
  if [[ "${recent:-0}" -ge 3 ]]; then
    mode="storm"
  elif [[ "${recent:-0}" -ge 1 ]]; then
    mode="alert"
  elif [[ -n "$last_alert" && $((now - last_alert)) -lt 86400 ]]; then
    mode="alert"
  fi
  echo "$mode"
}

nexus_vigil_recompute_mode() {
  local mode last_alert="${1:-}"
  mode="$(nexus_vigil_compute_mode)"
  [[ -n "$last_alert" ]] || last_alert="$(grep '^last_alert=' "$NEXUS_VIGIL_STATE" 2>/dev/null | cut -d= -f2)"
  last_alert="${last_alert:-0}"
  nexus_vigil_write_state "$mode" "$last_alert"
}

nexus_vigil_get_mode() {
  local mode
  mode="$(nexus_vigil_compute_mode)"
  [[ "$(id -u)" -eq 0 && -w "$NEXUS_VIGIL_STATE" ]] && nexus_vigil_recompute_mode
  echo "$mode"
}

nexus_vigil_scan_interval() {
  local raw
  case "$(nexus_vigil_get_mode)" in
    storm) raw=5 ;;
    alert) raw=5 ;;
    *) raw=5 ;;
  esac
  if declare -f nexus_await_clamp >/dev/null 2>&1; then
    nexus_await_clamp "$raw"
  else
    printf '%s' "$raw"
  fi
}

nexus_vigil_entropy_threshold() {
  case "$(nexus_vigil_get_mode)" in
    storm) echo 6.5 ;;
    alert) echo 6.8 ;;
    *) echo 7.4 ;;
  esac
}

nexus_vigil_behavior_sensitivity() {
  case "$(nexus_vigil_get_mode)" in
    storm) echo 40 ;;
    alert) echo 50 ;;
    *) echo 50 ;;
  esac
}

nexus_vigil_prune_alerts() {
  local now cutoff tmp
  now="$(date +%s)"
  cutoff=$((now - 172800))
  tmp="$(mktemp "${NEXUS_STATE_DIR}/vigil-alerts.XXXXXX")"
  awk -v c="$cutoff" '$1 >= c' "$NEXUS_VIGIL_ALERTS" >"$tmp" 2>/dev/null && mv "$tmp" "$NEXUS_VIGIL_ALERTS"
  rm -f "$tmp"
}
