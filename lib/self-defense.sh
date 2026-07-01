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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/self-defense.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Self-defense — verify signed script manifest before loading modules.

NEXUS_MANIFEST="${NEXUS_MANIFEST:-${NEXUS_INSTALL_ROOT}/MANIFEST.sha256}"

nexus_manifest_paths() {
  find "${NEXUS_INSTALL_ROOT}/lib" -maxdepth 1 \( -name '*.sh' -o -name '*.py' \) -type f 2>/dev/null | sort
  find "${NEXUS_INSTALL_ROOT}/bin" -maxdepth 1 -type f 2>/dev/null | sort
  find "${NEXUS_INSTALL_ROOT}/panel" -type f 2>/dev/null | sort
  [[ -f "${NEXUS_INSTALL_ROOT}/config/nexus.conf" ]] && echo "${NEXUS_INSTALL_ROOT}/config/nexus.conf"
  [[ -f "${NEXUS_INSTALL_ROOT}/config/device-whitelist.conf" ]] && echo "${NEXUS_INSTALL_ROOT}/config/device-whitelist.conf"
  if [[ -f "${NEXUS_INSTALL_ROOT}/lib/nexus-executable-seal.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/nexus-executable-seal.sh"
    nexus_executable_paths 2>/dev/null | sort -u
  fi
}

nexus_manifest_unlock() {
  command -v chattr >/dev/null 2>&1 || return 0
  chattr -i "$NEXUS_MANIFEST" 2>/dev/null || true
}

nexus_manifest_lock() {
  command -v chattr >/dev/null 2>&1 || return 0
  [[ -f "$NEXUS_MANIFEST" ]] && chattr +i "$NEXUS_MANIFEST" 2>/dev/null || true
}

nexus_sign_manifest() {
  local out="${1:-$NEXUS_MANIFEST}"
  [[ "$out" == "$NEXUS_MANIFEST" ]] && nexus_manifest_unlock
  : >"$out"
  chmod 640 "$out" 2>/dev/null || true
  local path hash
  while IFS= read -r path; do
    [[ -f "$path" ]] || continue
    hash="$(sha256sum "$path" | awk '{print $1}')"
    printf '%s  %s\n' "$hash" "$path" >>"$out"
  done < <(nexus_manifest_paths)
  [[ "$out" == "$NEXUS_MANIFEST" ]] && nexus_manifest_lock
}

nexus_manifest_resolve_path() {
  local path="$1"
  [[ -f "$path" ]] && { printf '%s' "$path"; return 0; }
  local base="${path##*/}"
  [[ -n "$base" && -f "${NEXUS_INSTALL_ROOT}/lib/${base}" ]] && {
    printf '%s' "${NEXUS_INSTALL_ROOT}/lib/${base}"
    return 0
  }
  [[ -n "$base" && -f "${NEXUS_INSTALL_ROOT}/bin/${base}" ]] && {
    printf '%s' "${NEXUS_INSTALL_ROOT}/bin/${base}"
    return 0
  }
  local rel="${path#*${NEXUS_INSTALL_ROOT}/}"
  if [[ "$rel" != "$path" && -f "${NEXUS_INSTALL_ROOT}/${rel}" ]]; then
    printf '%s' "${NEXUS_INSTALL_ROOT}/${rel}"
    return 0
  fi
  rel="${path#*/panel/}"
  if [[ "$rel" != "$path" && -f "${NEXUS_INSTALL_ROOT}/panel/${rel}" ]]; then
    printf '%s' "${NEXUS_INSTALL_ROOT}/panel/${rel}"
    return 0
  fi
  printf '%s' "$path"
  return 1
}

nexus_verify_integrity() {
  [[ "${NEXUS_SELF_DEFENSE:-1}" == "1" ]] || return 0
  if declare -f nexus_is_dev_install >/dev/null 2>&1 && nexus_is_dev_install; then
    return 0
  fi
  [[ -f "$NEXUS_MANIFEST" ]] || {
    nexus_log "ALERT" "self-defense" "MANIFEST_MISSING"
    return 1
  }
  local fail=0 hash path resolved current
  while read -r hash path; do
    [[ -n "$hash" && -n "$path" ]] || continue
    resolved="$(nexus_manifest_resolve_path "$path" || true)"
    [[ -f "$resolved" ]] || {
      nexus_log "ALERT" "self-defense" "INTEGRITY_MISSING path=${path}"
      fail=1
      continue
    }
    current="$(sha256sum "$resolved" | awk '{print $1}')"
    if [[ "$current" != "$hash" ]]; then
      nexus_log "ALERT" "self-defense" "INTEGRITY_FAIL path=${resolved}"
      fail=1
    fi
  done <"$NEXUS_MANIFEST"
  if [[ "$fail" -eq 0 ]] && [[ -f "${NEXUS_INSTALL_ROOT}/lib/nexus-executable-seal.sh" ]]; then
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/nexus-executable-seal.sh"
    nexus_verify_executable_integrity || fail=1
  fi
  [[ "$fail" -eq 0 ]]
}

nexus_safe_source() {
  local script="$1"
  nexus_verify_integrity || {
    nexus_log "ALERT" "self-defense" "REFUSING_LOAD tampered=${script}"
    return 1
  }
  # shellcheck source=/dev/null
  source "$script"
}