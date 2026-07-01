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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:Queen/scripts/start-world.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Queen World — sovereign browser space on one RTX card (loopback only).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NEXUS_ROOT="$(cd "$ROOT/.." && pwd)"
_state_explicit=0
[[ -n "${NEXUS_STATE_DIR:-}" ]] && _state_explicit=1
_state_saved="${NEXUS_STATE_DIR:-}"
# shellcheck source=/dev/null
source "${NEXUS_ROOT}/lib/nexus-common.sh"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-${NEXUS_ROOT}}"
export NEXUS_FIELD_STANDALONE=1
nexus_init_runtime_paths
if [[ "$_state_explicit" -eq 1 ]]; then
  export NEXUS_STATE_DIR="$_state_saved"
fi
unset _state_explicit _state_saved

export QUEEN_ROOT="${ROOT}"
export QUEEN_SOVEREIGN=1
export NEXUS_QUEEN_SOVEREIGN=1
export NEXUS_EMBED_PANEL_IN_ENGINE=0
export QUEEN_FIELD_GPU=1
export HOSTESS7_ROOT="${HOSTESS7_ROOT:-${ROOT}/../../Hostess7}"
export QUEEN_WORLD_HOST="${QUEEN_WORLD_HOST:-127.0.0.1}"
export QUEEN_WORLD_PORT="${QUEEN_WORLD_PORT:-9481}"

if [[ "${1:-}" == "--daemon" ]]; then
  # shellcheck source=/dev/null
  [[ -f "${NEXUS_ROOT}/lib/queen-layer-boot.sh" ]] && source "${NEXUS_ROOT}/lib/queen-layer-boot.sh"
  if declare -f nexus_queen_world_ensure >/dev/null 2>&1; then
    nexus_queen_world_ensure
    exit $?
  fi
fi

exec "${ROOT}/scripts/queen-py" "${ROOT}/lib/queen-world.py" --host "${QUEEN_WORLD_HOST}" --port "${QUEEN_WORLD_PORT}" "$@"