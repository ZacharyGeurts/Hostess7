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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/sg-paths.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# SG portable path resolution — no operator-specific defaults; env + sibling discovery only.

sg_paths_root() {
  if [[ -n "${NEXUS_INSTALL_ROOT:-}" && -d "${NEXUS_INSTALL_ROOT}/lib" ]]; then
    printf '%s\n' "$(cd "${NEXUS_INSTALL_ROOT}" && pwd)"
    return 0
  fi
  if [[ -n "${SG_ROOT:-}" ]]; then
    printf '%s\n' "$(cd "${SG_ROOT}" && pwd)"
    return 0
  fi
  if [[ -n "${BASH_SOURCE[1]:-}" ]]; then
    local lib tree
    lib="$(cd "$(dirname "${BASH_SOURCE[1]}")" && pwd)"
    tree="$(cd "${lib}/.." && pwd)"
    if [[ -d "${tree}/lib" ]]; then
      printf '%s\n' "$tree"
      return 0
    fi
    printf '%s\n' "$(cd "${tree}/.." && pwd)"
    return 0
  fi
  printf '%s\n' "$(pwd)"
}

sg_paths_stack_child() {
  local name="$1"
  shift || true
  local sg parent candidate resolved=""
  sg="$(sg_paths_root)"
  parent="$(cd "${sg}/.." 2>/dev/null && pwd || true)"
  if [[ -e "${sg}/${name}" ]]; then
    printf '%s\n' "$(cd "${sg}/${name}" && pwd)"
    return 0
  fi
  for candidate in "$@"; do
    [[ -e "${sg}/${candidate}" ]] || continue
    printf '%s\n' "$(cd "${sg}/${candidate}" && pwd)"
    return 0
  done
  if [[ -n "$parent" && -e "${parent}/${name}" ]]; then
    printf '%s\n' "$(cd "${parent}/${name}" && pwd)"
    return 0
  fi
  printf '%s\n' "${sg}/${name}"
}

sg_paths_hostess7_root() {
  if [[ -n "${HOSTESS7_ROOT:-}" ]]; then
    printf '%s\n' "$(cd "${HOSTESS7_ROOT}" && pwd)"
    return 0
  fi
  if [[ -n "${NEXUS_INSTALL_ROOT:-}" && -d "${NEXUS_INSTALL_ROOT}/Hostess7" ]]; then
    printf '%s\n' "$(cd "${NEXUS_INSTALL_ROOT}/Hostess7" && pwd)"
    return 0
  fi
  local sg
  sg="$(sg_paths_root)"
  printf '%s\n' "${sg}/Hostess7"
}

sg_paths_hostess7_team_field() {
  if [[ -n "${HOSTESS7_TEAM_FIELD:-}" ]]; then
    printf '%s\n' "${HOSTESS7_TEAM_FIELD}"
    return 0
  fi
  local mount candidate
  if [[ -d /media ]]; then
    for mount in /media/*/; do
      [[ -d "$mount" ]] || continue
      for candidate in \
        "${mount}HOSTESS7_TEAM/fieldstorage" \
        "${mount}fieldstorage" \
        "${mount}HOSTESS7_TEAM"; do
        [[ -d "$candidate" ]] || continue
        printf '%s\n' "$(cd "$candidate" && pwd)"
        return 0
      done
    done
  fi
  local h7
  h7="$(sg_paths_hostess7_root)"
  printf '%s\n' "${h7}/cache/fieldstorage"
}

sg_paths_hostess7_team1_field() {
  [[ -n "${HOSTESS7_TEAM1_FIELD:-}" ]] && printf '%s\n' "${HOSTESS7_TEAM1_FIELD}"
}

sg_paths_hostess7_nexus_cache() {
  if [[ -n "${HOSTESS7_NEXUS_CACHE:-}" ]]; then
    printf '%s\n' "${HOSTESS7_NEXUS_CACHE}"
    return 0
  fi
  local state="${NEXUS_STATE_DIR:-/var/lib/nexus-shield}"
  printf '%s\n' "${state%/}/hostess7-cache/fieldstorage"
}

sg_paths_final_eye_root() {
  if [[ -n "${FINAL_EYE_ROOT:-}" ]]; then
    printf '%s\n' "$(cd "${FINAL_EYE_ROOT}" 2>/dev/null && pwd || echo "${FINAL_EYE_ROOT}")"
    return 0
  fi
  local candidate resolved=""
  for candidate in Final_Eye; do
    resolved="$(sg_paths_stack_child "$candidate" 2>/dev/null || true)"
    [[ -n "$resolved" && -e "$resolved" ]] || continue
    printf '%s\n' "$resolved"
    return 0
  done
  sg_paths_stack_child "Final_Eye"
}

sg_paths_znewocr_root() {
  sg_paths_final_eye_root
}

sg_paths_znetwork_root() {
  if [[ -n "${ZNETWORK_ROOT:-}" ]]; then
    printf '%s\n' "$(cd "${ZNETWORK_ROOT}" 2>/dev/null && pwd || echo "${ZNETWORK_ROOT}")"
    return 0
  fi
  if [[ -n "${NEXUS_INSTALL_ROOT:-}" && -d "${NEXUS_INSTALL_ROOT}/ZNetwork" ]]; then
    printf '%s\n' "$(cd "${NEXUS_INSTALL_ROOT}/ZNetwork" && pwd)"
    return 0
  fi
  local sg parent
  sg="$(sg_paths_root)"
  if [[ -d "${sg}/ZNetwork" ]]; then
    printf '%s\n' "$(cd "${sg}/ZNetwork" && pwd)"
    return 0
  fi
  parent="$(cd "${sg}/.." 2>/dev/null && pwd || true)"
  if [[ -n "$parent" && -d "${parent}/NewLatest/ZNetwork" ]]; then
    printf '%s\n' "$(cd "${parent}/NewLatest/ZNetwork" && pwd)"
    return 0
  fi
  local integrated="${NEXUS_INSTALL_ROOT:-}/znetwork"
  if [[ -d "${integrated}" ]]; then
    printf '%s\n' "$(cd "${integrated}" && pwd)"
    return 0
  fi
  sg_paths_stack_child "ZNetwork" "znetwork"
}

sg_paths_znetwork_bin() {
  if [[ -n "${ZNETWORK_BIN:-}" && -x "${ZNETWORK_BIN}" ]]; then
    printf '%s\n' "${ZNETWORK_BIN}"
    return 0
  fi
  local root candidate
  root="$(sg_paths_znetwork_root)"
  for candidate in \
    "${root}/build/znetwork" \
    "${NEXUS_INSTALL_ROOT:-}/bin/znetwork" \
    "${NEXUS_INSTALL_ROOT:-}/ZNetwork/build/znetwork"; do
    [[ -n "$candidate" && -x "$candidate" ]] || continue
    printf '%s\n' "$(cd "$(dirname "$candidate")" && pwd)/$(basename "$candidate")"
    return 0
  done
  return 1
}

sg_paths_queen_root() {
  if [[ -n "${QUEEN_ROOT:-}" && -d "${QUEEN_ROOT}" ]]; then
    printf '%s\n' "$(cd "${QUEEN_ROOT}" && pwd)"
    return 0
  fi
  local sg parent candidate
  sg="$(sg_paths_root)"
  parent="$(cd "${sg}/.." 2>/dev/null && pwd || true)"
  for candidate in \
    "${NEXUS_INSTALL_ROOT:-}/Queen" \
    "${sg}/Queen" \
    "${sg}/NewLatest/Queen" \
    "${parent}/SG/Queen" \
    "${parent}/SG/NewLatest/Queen" \
    "${HOME:-/home/default}/Desktop/SG/Queen" \
    "${HOME:-/home/default}/Desktop/SG/NewLatest/Queen"; do
    [[ -n "$candidate" ]] || continue
    [[ -d "${candidate}/world" || -d "${candidate}/lib" ]] || continue
    printf '%s\n' "$(cd "${candidate}" && pwd)"
    return 0
  done
  printf '%s\n' "${sg}/Queen"
}

sg_paths_ammocode_root() {
  if [[ -n "${AMMOCODE_ROOT:-}" ]]; then
    printf '%s\n' "$(cd "${AMMOCODE_ROOT}" 2>/dev/null && pwd || echo "${AMMOCODE_ROOT}")"
    return 0
  fi
  sg_paths_stack_child "AmmoCode"
}

sg_paths_grok16_root() {
  local inst parent candidate resolved=""
  if [[ -n "${GROK16_ROOT:-}" && -x "${GROK16_ROOT}/bin/g16" ]]; then
    printf '%s\n' "$(cd "${GROK16_ROOT}" && pwd)"
    return 0
  fi
  inst="$(sg_paths_root)"
  parent="$(cd "${inst}/.." 2>/dev/null && pwd || true)"
  for candidate in "${inst}/Grok16" "${parent}/Grok16"; do
    [[ -x "${candidate}/bin/g16" ]] || continue
    printf '%s\n' "$(cd "${candidate}" && pwd)"
    return 0
  done
  sg_paths_stack_child Grok16
}

sg_paths_export_defaults() {
  export HOME="${HOME:-/home/default}"
  export USER="${USER:-$(id -un 2>/dev/null || echo default)}"
  export SG_ROOT="${SG_ROOT:-$(sg_paths_root)}"
  export QUEEN_ROOT="${QUEEN_ROOT:-$(sg_paths_queen_root)}"
  export HOSTESS7_ROOT="${HOSTESS7_ROOT:-$(sg_paths_hostess7_root)}"
  export HOSTESS7_TEAM_FIELD="${HOSTESS7_TEAM_FIELD:-$(sg_paths_hostess7_team_field)}"
  export HOSTESS7_NEXUS_CACHE="${HOSTESS7_NEXUS_CACHE:-$(sg_paths_hostess7_nexus_cache)}"
  export FINAL_EYE_ROOT="${FINAL_EYE_ROOT:-$(sg_paths_final_eye_root)}"
  export ZNETWORK_ROOT="${ZNETWORK_ROOT:-$(sg_paths_znetwork_root)}"
  export ZNETWORK_BIN="${ZNETWORK_BIN:-$(sg_paths_znetwork_bin 2>/dev/null || true)}"
  export NEXUS_SHIELD_SOURCE="${NEXUS_SHIELD_SOURCE:-${NEXUS_INSTALL_ROOT:-}}"
  export GROK16_ROOT="${GROK16_ROOT:-$(sg_paths_grok16_root)}"
  export AMMOCODE_ROOT="${AMMOCODE_ROOT:-$(sg_paths_ammocode_root)}"
  export KILROY_ROOT="${KILROY_ROOT:-$(sg_paths_stack_child KILROY)}"
  export PYTHONG_ROOT="${PYTHONG_ROOT:-$(sg_paths_stack_child PythonG)}"
  export GROKPY_ROOT="${GROKPY_ROOT:-$(sg_paths_stack_child GrokPy)}"
  export AMOURANTHRTX_ROOT="${AMOURANTHRTX_ROOT:-$(sg_paths_stack_child AMOURANTHRTX)}"
  export WORLD_REDATA_ROOT="${WORLD_REDATA_ROOT:-$(sg_paths_stack_child World_Redata)}"
}