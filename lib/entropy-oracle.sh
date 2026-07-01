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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/entropy-oracle.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Entropy Oracle — Shannon entropy heuristics for new files.

NEXUS_ENTROPY_SAMPLE="${NEXUS_ENTROPY_SAMPLE:-65536}"
NEXUS_ENTROPY_WATCH_DIRS=(
  /tmp
)

nexus_entropy_add_user_dirs() {
  local home
  for home in /home/* /root; do
    [[ -d "$home/Downloads" ]] && NEXUS_ENTROPY_WATCH_DIRS+=("${home}/Downloads")
    [[ -d "$home/Desktop" ]] && NEXUS_ENTROPY_WATCH_DIRS+=("${home}/Desktop")
  done
}

nexus_entropy_score() {
  local file="$1"
  [[ -f "$file" ]] || { echo 0; return; }
  od -An -tu1 -N "$NEXUS_ENTROPY_SAMPLE" "$file" 2>/dev/null | tr -s ' \n' '\n' | awk '
    NF { count[$1]++; total++ }
    END {
      if (total == 0) { print 0; exit }
      h = 0
      for (b in count) {
        p = count[b] / total
        h -= p * (log(p) / log(2))
      }
      printf "%.4f", h
    }'
}

nexus_entropy_check_file() {
  local file="$1"
  local threshold score
  threshold="$(nexus_vigil_entropy_threshold)"
  nexus_extension_allowlisted "$file" && return 0
  score="$(nexus_entropy_score "$file")"
  awk -v s="$score" -v t="$threshold" 'BEGIN { exit (s >= t) ? 1 : 0 }' && return 0
  nexus_alert "entropy-oracle" "ENTROPY_ORACLE_ALERT path=${file} entropy=${score} threshold=${threshold}"
  return 1
}

nexus_entropy_watch() {
  nexus_entropy_add_user_dirs
  command -v inotifywait >/dev/null 2>&1 || {
    nexus_log "WARN" "entropy-oracle" "inotifywait missing; entropy watch idle"
    return 0
  }
  local existing=()
  local dir
  for dir in "${NEXUS_ENTROPY_WATCH_DIRS[@]}"; do
    [[ -d "$dir" ]] && existing+=("$dir")
  done
  [[ ${#existing[@]} -eq 0 ]] && return 0
  inotifywait -m -e create,modify --format '%w%f' "${existing[@]}" 2>/dev/null | while read -r newfile; do
    [[ -f "$newfile" ]] || continue
    nexus_entropy_check_file "$newfile" || true
  done
}