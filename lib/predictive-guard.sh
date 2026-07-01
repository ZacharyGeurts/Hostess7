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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/predictive-guard.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Predictive guard — correlate recent alerts to pre-tighten before escalation.

NEXUS_PREDICTIVE_STATE="${NEXUS_PREDICTIVE_STATE:-${NEXUS_STATE_DIR}/predictive.state}"

nexus_predictive_init() {
  [[ "${NEXUS_PREDICTIVE:-1}" == "1" ]] || return 0
  mkdir -p "$(dirname "$NEXUS_PREDICTIVE_STATE")"
  [[ -f "$NEXUS_PREDICTIVE_STATE" ]] || echo "score=0" >"$NEXUS_PREDICTIVE_STATE"
}

nexus_predictive_record() {
  local module="$1"
  local weight=1
  case "$module" in
    entropy-oracle) weight=2 ;;
    behavior-symphony) weight=3 ;;
    shadow-reality|privacy-guard) weight=2 ;;
    packet-oracle|threat-vectors|firewall-sentinel) weight=4 ;;
    self-defense) weight=5 ;;
  esac
  local score
  score="$(grep '^score=' "$NEXUS_PREDICTIVE_STATE" 2>/dev/null | cut -d= -f2)"
  score=$(( ${score:-0} + weight ))
  sed -i "s/^score=.*/score=${score}/" "$NEXUS_PREDICTIVE_STATE" 2>/dev/null || echo "score=${score}" >"$NEXUS_PREDICTIVE_STATE"
  if [[ "$score" -ge 6 ]]; then
    nexus_vigil_record_alert "predictive-guard"
    nexus_log "INFO" "predictive-guard" "PREDICTIVE_TIGHTEN score=${score} modules_correlated"
  fi
}

nexus_predictive_decay() {
  local score
  score="$(grep '^score=' "$NEXUS_PREDICTIVE_STATE" 2>/dev/null | cut -d= -f2)"
  score=$(( ${score:-0} > 0 ? score - 1 : 0 ))
  sed -i "s/^score=.*/score=${score}/" "$NEXUS_PREDICTIVE_STATE" 2>/dev/null || true
}