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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/behavior-symphony.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Behavior Symphony — procfs fork/exec chain scoring.

NEXUS_BEHAVIOR_CHAIN_DB="${NEXUS_BEHAVIOR_CHAIN_DB:-${NEXUS_BEHAVIOR_DIR}/chains.tsv}"
NEXUS_BEHAVIOR_WINDOW=3

nexus_behavior_init() {
  nexus_ensure_dirs || return 1
  : >"$NEXUS_BEHAVIOR_CHAIN_DB"
}

nexus_behavior_parent() {
  local pid="$1"
  awk '/^PPid:/ {print $2; exit}' "/proc/${pid}/status" 2>/dev/null
}

nexus_behavior_comm() {
  local pid="$1"
  [[ -r "/proc/${pid}/comm" ]] || { echo unknown; return 0; }
  tr -d '\0' <"/proc/${pid}/comm" 2>/dev/null || echo unknown
}

nexus_behavior_exe() {
  local pid="$1"
  readlink -f "/proc/${pid}/exe" 2>/dev/null || echo ""
}

nexus_behavior_chain_depth() {
  local pid="$1" depth=0 ppid
  while [[ -n "$pid" && "$pid" != "0" && $depth -lt 12 ]]; do
    depth=$((depth + 1))
    ppid="$(nexus_behavior_parent "$pid")"
    pid="$ppid"
  done
  echo "$depth"
}

nexus_behavior_score_pid() {
  local pid="$1"
  local score=0 depth comm exe ppid
  depth="$(nexus_behavior_chain_depth "$pid")"
  comm="$(nexus_behavior_comm "$pid")"
  exe="$(nexus_behavior_exe "$pid")"
  [[ "$depth" -gt 4 ]] && score=$((score + 30))
  case "$exe" in
    /tmp/*|/dev/shm/*|*/.cache/*) score=$((score + 20)) ;;
  esac
  [[ "$comm" != */* && "$comm" != "bash" && "$comm" != "sh" ]] && score=$((score + 10))
  ppid="$(nexus_behavior_parent "$pid")"
  if [[ -n "$ppid" ]]; then
    local pcomm pexe
    pcomm="$(nexus_behavior_comm "$ppid")"
    pexe="$(nexus_behavior_exe "$ppid")"
    case "$pcomm" in
      wget|curl|fetch) score=$((score + 40)) ;;
    esac
    case "$pexe" in
      /tmp/*|/dev/shm/*) score=$((score + 20)) ;;
    esac
  fi
  echo "$score"
}

nexus_behavior_snapshot() {
  local now pid score comm exe
  now="$(date +%s)"
  # shellcheck source=/dev/null
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/device-whitelist.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/device-whitelist.sh"
  for pid_path in /proc/[0-9]*; do
    pid="${pid_path##*/}"
    [[ "$pid" =~ ^[0-9]+$ ]] || continue
    comm="$(nexus_behavior_comm "$pid")"
    exe="$(nexus_behavior_exe "$pid")"
    if command -v nexus_is_whitelisted_process >/dev/null 2>&1; then
      nexus_is_whitelisted_process "$comm" "$exe" && continue
    fi
    score="$(nexus_behavior_score_pid "$pid")"
    printf '%s\t%s\t%s\t%s\t%s\n' "$now" "$pid" "$score" "$comm" "$exe" >>"$NEXUS_BEHAVIOR_CHAIN_DB"
  done
}

nexus_behavior_evaluate() {
  local threshold now cutoff max_score line pid score comm exe
  threshold="$(nexus_vigil_behavior_sensitivity)"
  now="$(date +%s)"
  cutoff=$((now - NEXUS_BEHAVIOR_WINDOW))
  max_score=0
  while IFS=$'\t' read -r ts pid score comm exe; do
    [[ "$ts" -ge "$cutoff" ]] || continue
    [[ "$score" -gt "$max_score" ]] && max_score="$score"
    if [[ "$score" -ge "$threshold" ]]; then
      nexus_alert "behavior-symphony" "BEHAVIOR_SYMPHONY_ALERT pid=${pid} score=${score} comm=${comm} exe=${exe}"
    fi
  done <"$NEXUS_BEHAVIOR_CHAIN_DB"
  awk -v c="$cutoff" '$1 >= c' "$NEXUS_BEHAVIOR_CHAIN_DB" >"${NEXUS_BEHAVIOR_CHAIN_DB}.tmp" 2>/dev/null \
    && mv "${NEXUS_BEHAVIOR_CHAIN_DB}.tmp" "$NEXUS_BEHAVIOR_CHAIN_DB"
}

nexus_behavior_loop() {
  nexus_behavior_init
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/ultra-stealth.sh"
  while true; do
    nexus_cpu_budget_ok || { sleep 10; continue; }
    nexus_behavior_snapshot
    nexus_behavior_evaluate
    sleep "$(nexus_adaptive_poll_interval behavior)"
  done
}