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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/tamper-guard.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Tamper Guard — verify protective shell, auto-restore from seal vault.
# Never restores training, brain expansion, or Hostess 7 biology paths.

[[ -f "${NEXUS_INSTALL_ROOT}/lib/nexus-biology-mutable.sh" ]] && {
  # shellcheck source=/dev/null
  source "${NEXUS_INSTALL_ROOT}/lib/nexus-biology-mutable.sh"
}

nexus_tamper_guard_cycle() {
  [[ "${NEXUS_TAMPER_GUARD:-1}" == "1" ]] || return 0
  nexus_verify_integrity && return 0
  nexus_alert "tamper-guard" "TAMPER_GUARD_ALERT integrity_fail"
  [[ "${NEXUS_TAMPER_AUTO_RESTORE:-1}" == "1" ]] || return 1
  nexus_tamper_restore_from_seal
  nexus_sign_manifest
  nexus_verify_integrity
}

nexus_tamper_restore_from_seal() {
  [[ -f "${NEXUS_SEAL_MANIFEST:-${NEXUS_STATE_DIR}/sealed/MANIFEST.sealed}" ]] || return 1
  nexus_seal_unseal
  local fail=0 hash path rel install_path current
  while read -r hash path; do
    [[ -n "$hash" && -n "$path" ]] || continue
    rel="${path#./}"
    install_path="${NEXUS_INSTALL_ROOT}/${rel}"
    declare -f nexus_path_is_biology_mutable >/dev/null 2>&1 && nexus_path_is_biology_mutable "$install_path" && continue
    [[ -f "$install_path" ]] || { nexus_seal_restore_path "$install_path" || fail=1; continue; }
    current="$(sha256sum "$install_path" | awk '{print $1}')"
    [[ "$current" == "$hash" ]] && continue
    nexus_seal_restore_path "$install_path" || fail=1
  done <"${NEXUS_SEAL_MANIFEST}"
  nexus_manifest_unlock
  command -v chattr >/dev/null 2>&1 && chattr -R +i "${NEXUS_SEAL_DIR}" 2>/dev/null || true
  [[ "$fail" -eq 0 ]]
}