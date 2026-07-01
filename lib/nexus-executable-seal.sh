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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/nexus-executable-seal.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Sign and seal built executables — MANIFEST.sha256 + seal vault + immutable bit on production.

NEXUS_EXECUTABLE_MANIFEST="${NEXUS_EXECUTABLE_MANIFEST:-${NEXUS_INSTALL_ROOT}/MANIFEST.executables.sha256}"
NEXUS_EXECUTABLE_SEAL_JSON="${NEXUS_EXECUTABLE_SEAL_JSON:-${NEXUS_STATE_DIR}/nexus-executable-seal.json}"

nexus_executable_search_roots() {
  local root="${NEXUS_INSTALL_ROOT}"
  printf '%s\n' \
    "${root}/bin" \
    "${root}/lib/bin" \
    "${root}/PythonG/bin" \
    "${root}/Grok16/bin" \
    "${root}/Queen/bin" \
    "${root}/Queen/scripts" \
    "${root}/KILROY/bin" \
    "${root}/Hostess7/bin"
}

nexus_executable_paths() {
  local dir path
  while IFS= read -r dir; do
    [[ -d "$dir" ]] || continue
    while IFS= read -r -d '' path; do
      [[ -f "$path" && -x "$path" ]] || continue
      printf '%s\n' "$path"
    done < <(find "$dir" -maxdepth 2 -type f -perm -111 -print0 2>/dev/null || true)
  done < <(nexus_executable_search_roots)
  if [[ -d "${NEXUS_INSTALL_ROOT}/dist" ]]; then
    while IFS= read -r -d '' path; do
      [[ -f "$path" && -x "$path" ]] || continue
      printf '%s\n' "$path"
    done < <(find "${NEXUS_INSTALL_ROOT}/dist" -maxdepth 4 -type f -perm -111 -print0 2>/dev/null || true)
  fi
}

nexus_executable_unlock() {
  command -v chattr >/dev/null 2>&1 || return 0
  local path
  while IFS= read -r path; do
    [[ -f "$path" ]] && chattr -i "$path" 2>/dev/null || true
  done < <(nexus_executable_paths)
  chattr -i "$NEXUS_EXECUTABLE_MANIFEST" 2>/dev/null || true
}

nexus_executable_lock() {
  [[ "${NEXUS_SEAL_EXECUTABLES_IMMUTABLE:-1}" == "1" ]] || return 0
  if declare -f nexus_is_dev_install >/dev/null 2>&1 && nexus_is_dev_install; then
    return 0
  fi
  command -v chattr >/dev/null 2>&1 || return 0
  local path
  while IFS= read -r path; do
    [[ -f "$path" ]] && chattr +i "$path" 2>/dev/null || true
  done < <(nexus_executable_paths)
  [[ -f "$NEXUS_EXECUTABLE_MANIFEST" ]] && chattr +i "$NEXUS_EXECUTABLE_MANIFEST" 2>/dev/null || true
}

nexus_sign_executable_manifest() {
  local out="${1:-$NEXUS_EXECUTABLE_MANIFEST}"
  nexus_executable_unlock
  : >"$out"
  chmod 640 "$out" 2>/dev/null || true
  local path hash count=0
  while IFS= read -r path; do
    [[ -f "$path" ]] || continue
    hash="$(sha256sum "$path" | awk '{print $1}')"
    printf '%s  %s\n' "$hash" "$path" >>"$out"
    count=$((count + 1))
  done < <(nexus_executable_paths | sort -u)
  printf '%s\n' "$count"
}

nexus_verify_executable_integrity() {
  [[ "${NEXUS_SELF_DEFENSE:-1}" == "1" ]] || return 0
  if declare -f nexus_is_dev_install >/dev/null 2>&1 && nexus_is_dev_install; then
    return 0
  fi
  [[ -f "$NEXUS_EXECUTABLE_MANIFEST" ]] || return 0
  local fail=0 hash path current
  while read -r hash path; do
    [[ -n "$hash" && -n "$path" ]] || continue
    [[ -f "$path" ]] || { fail=1; continue; }
    current="$(sha256sum "$path" | awk '{print $1}')"
    [[ "$current" == "$hash" ]] || fail=1
  done <"$NEXUS_EXECUTABLE_MANIFEST"
  [[ "$fail" -eq 0 ]]
}

nexus_seal_built_executables() {
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/self-defense.sh" ]] || return 1
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/self-defense.sh"
  [[ -f "${NEXUS_INSTALL_ROOT}/lib/seal-vault.sh" ]] && {
    # shellcheck source=/dev/null
    source "${NEXUS_INSTALL_ROOT}/lib/seal-vault.sh"
  }

  local count
  count="$(nexus_sign_executable_manifest)"
  nexus_sign_manifest "${NEXUS_INSTALL_ROOT}/MANIFEST.sha256" 2>/dev/null || true
  if declare -f nexus_seal_refresh >/dev/null 2>&1; then
    nexus_seal_refresh || true
  fi
  nexus_executable_lock

  mkdir -p "${NEXUS_STATE_DIR}"
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -Iseconds)"
  cat >"${NEXUS_EXECUTABLE_SEAL_JSON}" <<EOF
{
  "schema": "nexus-executable-seal/v1",
  "sealed": true,
  "updated": "${ts}",
  "executable_count": ${count:-0},
  "manifest": "${NEXUS_EXECUTABLE_MANIFEST}",
  "integrity_manifest": "${NEXUS_INSTALL_ROOT}/MANIFEST.sha256",
  "immutable": $([[ "${NEXUS_SEAL_EXECUTABLES_IMMUTABLE:-1}" == "1" ]] && echo true || echo false),
  "policy": "Built executables signed in MANIFEST.executables.sha256; install MANIFEST.sha256 refreshed; seal vault snapshot; production paths locked against tamper."
}
EOF
  chmod 640 "${NEXUS_EXECUTABLE_SEAL_JSON}" 2>/dev/null || true
  nexus_log "INFO" "executable-seal" "SEALED count=${count:-0}"
  return 0
}