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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/nexus-boot-impl.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Standalone boot-impl entry — systemd ExecStartPre or manual re-apply.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export SG_ROOT="${SG_ROOT:-$ROOT}"

_state_explicit=0
[[ -n "${NEXUS_STATE_DIR:-}" ]] && _state_explicit=1
_state_saved="${NEXUS_STATE_DIR:-}"

_nexus_boot_impl_restore_state() {
  if [[ "$_state_explicit" -eq 1 ]]; then
    NEXUS_STATE_DIR="$_state_saved"
    export NEXUS_STATE_DIR
  fi
}

# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/nexus-common.sh"
nexus_init_runtime_paths
_nexus_boot_impl_restore_state
nexus_load_config 2>/dev/null || true
_nexus_boot_impl_restore_state
unset _state_explicit _state_saved

# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/nexus-boot-impl.sh"
nexus_boot_impl_run