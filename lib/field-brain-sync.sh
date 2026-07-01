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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/field-brain-sync.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Field brain + library — GitHub repo is authoritative; field drive enriches when mounted.

nexus_field_brain_score() {
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

nexus_field_brain_bytes() {
  local brain="${1}/brain"
  [[ -d "$brain" ]] || return 0
  du -sb "$brain" 2>/dev/null | awk '{print $1}' || printf '0'
}

# shellcheck source=/dev/null
[[ -f "${NEXUS_INSTALL_ROOT:-}/lib/sg-paths.sh" ]] && source "${NEXUS_INSTALL_ROOT}/lib/sg-paths.sh"
[[ -f "$(dirname "${BASH_SOURCE[0]}")/sg-paths.sh" ]] && source "$(dirname "${BASH_SOURCE[0]}")/sg-paths.sh"
sg_paths_export_defaults 2>/dev/null || true

nexus_field_brain_candidates() {
  local h7="${HOSTESS7_ROOT:-$(sg_paths_hostess7_root 2>/dev/null)}"
  local cache="${h7}/cache/fieldstorage"
  if [[ -n "${HOSTESS7_TEAM_FIELD:-}" && "${HOSTESS7_TEAM_FIELD}" != "${cache}" ]]; then
    printf '%s\n' "${HOSTESS7_TEAM_FIELD}"
  fi
  [[ -n "${HOSTESS7_TEAM1_FIELD:-}" ]] && printf '%s\n' "${HOSTESS7_TEAM1_FIELD}"
  printf '%s\n' "$cache" "${HOSTESS7_NEXUS_CACHE:-$(sg_paths_hostess7_nexus_cache 2>/dev/null)}"
}

nexus_field_brain_best_root() {
  local best="" score best_score=0 best_bytes=0 s b candidate
  while IFS= read -r candidate; do
    [[ -d "$candidate" ]] || continue
    s="$(nexus_field_brain_score "$candidate")"
    b="$(nexus_field_brain_bytes "$candidate")"
    if [[ "$s" -gt "$best_score" ]] || { [[ "$s" -eq "$best_score" ]] && [[ "$b" -gt "$best_bytes" ]]; }; then
      best_score="$s"
      best_bytes="$b"
      best="$candidate"
    fi
  done < <(nexus_field_brain_candidates)
  [[ -n "$best" ]] || best="${HOSTESS7_ROOT:-$(sg_paths_hostess7_root 2>/dev/null)}/cache/fieldstorage"
  printf '%s' "$best"
}

nexus_field_brain_github_refresh() {
  [[ "${NEXUS_FIELD_BRAIN_GITHUB_FETCH:-1}" == "1" ]] || return 0
  local install="${NEXUS_INSTALL_ROOT}"
  [[ -d "${install}/.git" ]] || return 0
  command -v git >/dev/null 2>&1 || return 0
  (
    cd "$install" || exit 0
    GIT_TERMINAL_PROMPT=0 \
    GIT_SSH_COMMAND="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15" \
      timeout 30 git fetch origin main 2>/dev/null || true
    git checkout origin/main -- library/ data/field-brain 2>/dev/null \
      || git checkout origin/main -- library/ 2>/dev/null || true
  )
  nexus_log "INFO" "field-brain-sync" "GITHUB_REFRESH library/ data/field-brain from origin/main"
}

nexus_field_brain_sync() {
  [[ "${NEXUS_FIELD_BRAIN_SYNC:-1}" == "1" ]] || return 0
  local h7_root="${HOSTESS7_ROOT:-$(sg_paths_hostess7_root 2>/dev/null)}"
  local team="${HOSTESS7_TEAM_FIELD:-$(sg_paths_hostess7_team_field 2>/dev/null)}"
  local cache="${h7_root}/cache/fieldstorage"
  local install="${NEXUS_INSTALL_ROOT}"
  local data="${install}/data"
  local best
  best="$(nexus_field_brain_best_root)"

  nexus_field_brain_github_refresh

  mkdir -p "${data}/field-brain" 2>/dev/null || true

  # Enrich data/field-brain for GitHub when live field has fuller manifests.
  for src in "${best}/brain/library/manifest.json" "${best}/brain/library/field_fingerprint.json" \
    "${best}/brain/index.json" "${best}/brain/superintel/context.json"; do
    [[ -f "$src" ]] || continue
    base="$(basename "$src")"
    case "$base" in
      context.json) dest="context.json" ;;
      *) dest="$base" ;;
    esac
    install -m 644 "$src" "${data}/field-brain/${dest}" 2>/dev/null \
      || cp -f "$src" "${data}/field-brain/${dest}" 2>/dev/null || true
  done

  local gh_books=0
  if [[ -d "${install}/library/dewey" ]]; then
    gh_books="$(find "${install}/library/dewey" -name book.json 2>/dev/null | wc -l | tr -d ' ')"
  fi

  if [[ -f "${install}/lib/field-brain-panel.py" ]]; then
    NEXUS_INSTALL_ROOT="${install}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      HOSTESS7_ROOT="${h7_root}" HOSTESS7_TEAM_FIELD="${team}" \
      pythong "${install}/lib/field-brain-panel.py" panel >/dev/null 2>&1 || true
  fi

  if [[ -f "${install}/lib/h7-library-bridge.py" ]]; then
    NEXUS_INSTALL_ROOT="${install}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      HOSTESS7_ROOT="${h7_root}" HOSTESS7_TEAM_FIELD="${team}" \
      pythong "${install}/lib/h7-library-bridge.py" build >/dev/null 2>&1 || true
  fi

  nexus_log "INFO" "field-brain-sync" "BRAIN_SYNC github_books=${gh_books} field_root=${best}"
}
