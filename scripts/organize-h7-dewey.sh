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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/organize-h7-dewey.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Move flat textbooks/*.h7 into textbooks/dewey/{class}/ on Hostess7 TEAM field drive.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
# shellcheck source=/dev/null
source "${ROOT}/lib/sg-paths.sh"
sg_paths_export_defaults

if [[ "${1:-}" == "--dry-run" ]]; then
  pythong "${ROOT}/lib/h7-library-bridge.py" organize --dry-run
else
  pythong "${ROOT}/lib/h7-library-bridge.py" organize
fi