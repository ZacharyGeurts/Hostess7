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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/znetwork-login-boot.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# ZNetwork login autostart — restore host network, then board relayer (sole internet in/out).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export SG_ROOT="${SG_ROOT:-$(cd "$ROOT/.." && pwd)}"
export ZNETWORK_ROOT="${NEXUS_INSTALL_ROOT:-${SG_ROOT}/NewLatest}/ZNetwork"
export ZNETWORK_MODE=ACTIVE
export ZNETWORK_RELAYER=1
export ZNETWORK_UNDERHOOK=0
export ZNETWORK_FAST=1
export ZNETWORK_NO_REVIEW=1
export ZNETWORK_REVIEW_APPROVED=1
export ZNETWORK_LAB_GATE_OK=1
export ZNETWORK_OUTSIDE_LAB=1
export ZNETWORK_SMART_INSIDE=1
export ZNETWORK_TAKEOVER=0
export ZNETWORK_NEVER_HARM_OS=1
export NEXUS_NEVER_HARM_OS=1
export NEXUS_ZNETWORK=1
export NEXUS_ZNETWORK_NO_SUDO=0
export ZNETWORK_RETIRE_NM_SYSTEMD=0
export ZNETWORK_STARTUP_RETIRE="${ZNETWORK_STARTUP_RETIRE:-1}"

# shellcheck source=/dev/null
source "${ROOT}/lib/nexus-common.sh"
nexus_init_runtime_paths 2>/dev/null || true
nexus_load_config 2>/dev/null || true

LOG="${NEXUS_STATE_DIR}/znetwork-login-boot.log"
mkdir -p "${NEXUS_STATE_DIR}" 2>/dev/null || true
{
  echo "=== znetwork-login-boot $(date -u '+%Y-%m-%dT%H:%M:%SZ') ==="
  echo "install_root=${NEXUS_INSTALL_ROOT} state=${NEXUS_STATE_DIR}"
} >>"$LOG" 2>/dev/null || true

# shellcheck source=/dev/null
source "${ROOT}/lib/znetwork-field.sh"

nexus_znetwork_ensure_host_network >>"$LOG" 2>&1 || true
nexus_znetwork_startup_with_us >>"$LOG" 2>&1 || true

echo "znetwork-login-boot complete" >>"$LOG" 2>/dev/null || true