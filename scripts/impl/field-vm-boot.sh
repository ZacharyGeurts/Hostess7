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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/impl/field-vm-boot.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Implementation — delegates to AML field_vm_boot task; post-verify only.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export NEXUS_INSTALL_ROOT="${ROOT}"
export SG_ROOT="${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-state}"
export KILROY_LOAD_FAST="${KILROY_LOAD_FAST:-1}"

# shellcheck source=/dev/null
source "${ROOT}/lib/nexus-aml-exec.sh"
nexus_aml_exec task:field_vm_boot "$@"

PANEL="${NEXUS_THREAT_PANEL_PORT:-9477}"
QUEEN="${QUEEN_WORLD_PORT:-9481}"
TRAIN="${H7_TRAINING_VIEWER_PORT:-9488}"

printf '[field-vm-boot] verify surfaces\n'
for url in \
  "http://127.0.0.1:${PANEL}/field" \
  "http://127.0.0.1:${QUEEN}/api/status" \
  "http://127.0.0.1:${TRAIN}/"; do
  if curl -sf --max-time 8 "$url" >/dev/null 2>&1; then
    printf '[field-vm-boot]   UP  %s\n' "$url"
  else
    printf '[field-vm-boot]   --  %s (not ready)\n' "$url"
  fi
done