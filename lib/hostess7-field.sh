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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/hostess7-field.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Hostess7 unified fieldstorage — portable roots; optional TEAM mounts via env only.

# shellcheck source=/dev/null
[[ -f "${NEXUS_INSTALL_ROOT:-}/lib/sg-paths.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/sg-paths.sh"
[[ -f "$(dirname "${BASH_SOURCE[0]}")/sg-paths.sh" ]] && source "$(dirname "${BASH_SOURCE[0]}")/sg-paths.sh"
sg_paths_export_defaults 2>/dev/null || true

HOSTESS7_ROOT="${HOSTESS7_ROOT:-$(sg_paths_hostess7_root 2>/dev/null || printf '%s' "${SG_ROOT}/Hostess7")}"
HOSTESS7_NEXUS_CACHE="${HOSTESS7_NEXUS_CACHE:-$(sg_paths_hostess7_nexus_cache 2>/dev/null || printf '%s' "${NEXUS_STATE_DIR:-/var/lib/nexus-shield}/hostess7-cache/fieldstorage")}"

hostess7_field_brain_score() {
  local root="$1"
  local score=0
  [[ -d "${root}/brain" ]] && score=$((score + 5))
  [[ -f "${root}/brain/library/manifest.json" ]] && score=$((score + 80))
  [[ -f "${root}/brain/library/search_index.jsonl" ]] && score=$((score + 40))
  [[ -d "${root}/brain/superintel" ]] && score=$((score + 50))
  [[ -f "${root}/brain/superintel/context.json" ]] && score=$((score + 30))
  [[ -d "${root}/brain/sdf" ]] && score=$((score + 20))
  printf '%s' "$score"
}

hostess7_field_brain_bytes() {
  local brain="${1}/brain"
  [[ -d "$brain" ]] || return 0
  du -sb "$brain" 2>/dev/null | awk '{print $1}' || printf '0'
}

hostess7_field_brain_candidates() {
  local cache="${HOSTESS7_ROOT}/cache/fieldstorage"
  local nexus="${HOSTESS7_NEXUS_CACHE}"
  if [[ -n "${HOSTESS7_TEAM_FIELD:-}" && "${HOSTESS7_TEAM_FIELD}" != "${cache}" ]]; then
    printf '%s\n' "${HOSTESS7_TEAM_FIELD}"
  fi
  [[ -n "${HOSTESS7_TEAM1_FIELD:-}" ]] && printf '%s\n' "${HOSTESS7_TEAM1_FIELD}"
  printf '%s\n' "$cache" "$nexus"
}

hostess7_field_root() {
  local best="" score best_score=0 best_bytes=0 s b candidate
  while IFS= read -r candidate; do
    [[ -d "$candidate" ]] || continue
    s="$(hostess7_field_brain_score "$candidate")"
    b="$(hostess7_field_brain_bytes "$candidate")"
    if [[ "$s" -gt "$best_score" ]] || { [[ "$s" -eq "$best_score" ]] && [[ "$b" -gt "$best_bytes" ]]; }; then
      best_score="$s"
      best_bytes="$b"
      best="$candidate"
    fi
  done < <(hostess7_field_brain_candidates)
  if [[ -n "$best" ]]; then
    printf '%s\n' "$best"
    return 0
  fi
  printf '%s\n' "${HOSTESS7_ROOT}/cache/fieldstorage"
}

hostess7_security_paths() {
  local rel="$1"
  local root
  root="$(hostess7_field_root)"
  printf '%s\n' "${root}/${rel}"
  if [[ "${root}" != "${HOSTESS7_ROOT}/cache/fieldstorage" ]] \
    && [[ -d "${HOSTESS7_ROOT}/cache/fieldstorage" ]]; then
    printf '%s\n' "${HOSTESS7_ROOT}/cache/fieldstorage/${rel}"
  fi
}

hostess7_nexus_source() {
  local candidates=(
    "${NEXUS_SHIELD_SOURCE:-}"
    "${NEXUS_INSTALL_ROOT:-}"
    "${SG_ROOT:-}"
    "${HOSTESS7_ROOT}/.."
  )
  local p
  for p in "${candidates[@]}"; do
    [[ -n "$p" && -f "${p}/stealth_install.sh" ]] || continue
    printf '%s\n' "$p"
    return 0
  done
  return 1
}