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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:lib/znetwork-linux-replace.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# ZNetwork Linux replace — invisible handoff, no link drop, downloads preserved.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export SG_ROOT="${SG_ROOT:-$(cd "$ROOT/.." && pwd)}"
export NEXUS_ZNETWORK=1
export ZNETWORK_RELAYER=1
export ZNETWORK_UNDERHOOK=0
export ZNETWORK_SMART_INSIDE=1
export ZNETWORK_TAKEOVER=0
export ZNETWORK_NEVER_HARM_OS=1
export NEXUS_NEVER_HARM_OS=1
export NEXUS_ZNETWORK_NO_SUDO=1
export ZNETWORK_INVISIBLE_REPLACE=1
export ZNETWORK_LINK_PRESERVE=1
export ZNETWORK_DEFER_RETALIATE=1
export ZNETWORK_DEFER_TRAY="${ZNETWORK_DEFER_TRAY:-0}"
export ZNETWORK_MODE="${ZNETWORK_MODE:-ACTIVE}"
export NEXUS_PANEL_TRAY="${NEXUS_PANEL_TRAY:-1}"

# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/nexus-common.sh"
nexus_load_config 2>/dev/null || true
mkdir -p "$NEXUS_STATE_DIR"
# shellcheck source=/dev/null
source "${NEXUS_INSTALL_ROOT}/lib/znetwork-field.sh"

runner="${NEXUS_PYTHONG:-pythong}"
command -v "$runner" >/dev/null 2>&1 || runner="python3"

nexus_znetwork_relayer_py relay >/dev/null
nexus_znetwork_mark_running

(
  sleep "${ZNETWORK_ARM_DELAY_SEC:-12}"
  nexus_znetwork_relayer_py arm >/dev/null 2>&1 || true
  if [[ "${ZNETWORK_DEFER_TRAY:-0}" == "1" ]]; then
    nexus_znetwork_tray_silent >/dev/null 2>&1 || true
  else
    nexus_znetwork_tray_swap >/dev/null 2>&1 || true
  fi
) &

exit 0