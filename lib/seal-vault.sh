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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/seal-vault.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Seal Vault — protective shell snapshot only (lib/bin/panel/config).
# Never snapshots Hostess 7 biology, training, brain cache, or runtime state.

NEXUS_SEAL_DIR="${NEXUS_SEAL_DIR:-${NEXUS_STATE_DIR}/sealed}"
NEXUS_SEAL_MANIFEST="${NEXUS_SEAL_MANIFEST:-${NEXUS_SEAL_DIR}/MANIFEST.sealed}"

[[ -f "${NEXUS_INSTALL_ROOT}/lib/nexus-biology-mutable.sh" ]] && {
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/nexus-biology-mutable.sh"
}

nexus_seal_unseal() {
  command -v chattr >/dev/null 2>&1 || return 0
  chattr -R -i "${NEXUS_SEAL_DIR}" 2>/dev/null || true
}

nexus_seal_refresh() {
  [[ "${NEXUS_SEAL_VAULT:-1}" == "1" ]] || return 0
  nexus_seal_unseal
  rm -rf "${NEXUS_SEAL_DIR}"
  mkdir -p "${NEXUS_SEAL_DIR}"
  cp -a "${NEXUS_INSTALL_ROOT}/lib" "${NEXUS_INSTALL_ROOT}/bin" \
    "${NEXUS_INSTALL_ROOT}/panel" "${NEXUS_INSTALL_ROOT}/config" "${NEXUS_SEAL_DIR}/"
  (
    cd "${NEXUS_SEAL_DIR}" || exit 1
    find . -type f ! -name 'MANIFEST.sealed' -print0 | sort -z \
      | xargs -0 sha256sum >"${NEXUS_SEAL_MANIFEST}"
  )
  chmod 700 "${NEXUS_SEAL_DIR}"
  chmod 640 "${NEXUS_SEAL_MANIFEST}" 2>/dev/null || true
  chown -R root:nexus "${NEXUS_SEAL_DIR}" 2>/dev/null || true
  command -v chattr >/dev/null 2>&1 && chattr -R +i "${NEXUS_SEAL_DIR}" 2>/dev/null || true
  nexus_log "INFO" "seal-vault" "SEAL_REFRESH files=$(wc -l <"${NEXUS_SEAL_MANIFEST}" | tr -d ' ')"
}

nexus_seal_verify() {
  [[ "${NEXUS_SEAL_VAULT:-1}" == "1" ]] || return 0
  [[ -f "${NEXUS_SEAL_MANIFEST}" ]] || return 1
  local fail=0 hash path rel
  while read -r hash path; do
    [[ -n "$hash" && -n "$path" ]] || continue
    rel="${path#./}"
    [[ -f "${NEXUS_SEAL_DIR}/${rel}" ]] || { fail=1; continue; }
    current="$(sha256sum "${NEXUS_SEAL_DIR}/${rel}" | awk '{print $1}')"
    [[ "$current" == "$hash" ]] || fail=1
  done <"${NEXUS_SEAL_MANIFEST}"
  [[ "$fail" -eq 0 ]]
}

nexus_seal_restore_path() {
  local install_path="$1"
  local rel sealed_src
  declare -f nexus_path_is_biology_mutable >/dev/null 2>&1 && nexus_path_is_biology_mutable "$install_path" && return 0
  rel="${install_path#${NEXUS_INSTALL_ROOT}/}"
  sealed_src="${NEXUS_SEAL_DIR}/${rel}"
  [[ -f "$sealed_src" ]] || return 1
  install -m "$(stat -c '%a' "$sealed_src" 2>/dev/null || echo 750)" -o root -g nexus "$sealed_src" "$install_path" 2>/dev/null \
    || cp -a "$sealed_src" "$install_path"
  nexus_log "INFO" "seal-vault" "SEAL_RESTORE path=${install_path}"
}