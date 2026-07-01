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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/nexus-g16-recompile.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# AmmoLang subfolder route — AML_BUILD=1 (default)
_aml_find_root() {
  local d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  while [[ "$d" != "/" ]]; do
    [[ -f "$d/lib/ammolang-run.sh" ]] && echo "$d" && return 0
    d="$(dirname "$d")"
  done
  return 1
}
if [[ "${AML_BUILD:-1}" != "0" ]]; then
  _AML_ROOT="$(_aml_find_root 2>/dev/null || true)"
  if [[ -n "$_AML_ROOT" ]]; then
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" g16_recompile "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

# NEXUS ↔ Grok16 recompile — AmmoLang orchestrates when AML_BUILD=1.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export SG_ROOT="${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}"
export NEXUS_INSTALL_ROOT="${ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-state}"
export QUEEN_ROOT="${QUEEN_ROOT:-${ROOT}/Queen}"
if [[ "${AML_BUILD:-1}" != "0" && -f "${ROOT}/lib/ammolang-run.sh" ]]; then
  exec bash "${ROOT}/lib/ammolang-run.sh" g16_recompile "$@"
fi
PY="${NEXUS_PYTHONG:-pythong}"
[[ -x "$PY" ]] || PY="${SG_ROOT}/PythonG/bin/pythong"
[[ -x "$PY" ]] || PY="python3"
# shellcheck source=/dev/null
source "${ROOT}/lib/sg-paths.sh" 2>/dev/null || true
declare -f sg_paths_export_defaults >/dev/null 2>&1 && sg_paths_export_defaults
export G16_PREFIX="${G16_PREFIX:-${GROK16_ROOT}}"
exec "$PY" "${ROOT}/lib/nexus-g16-recompile.py" "${@:-recompile}"
