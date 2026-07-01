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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/sync-dewey-github.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Build World's Best Dewey Library tree for GitHub — browsable shelves + book manifests.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_REPO_ROOT="${NEXUS_REPO_ROOT:-$ROOT}"
export NEXUS_DEWEY_GITHUB_ROOT="${NEXUS_DEWEY_GITHUB_ROOT:-$ROOT/library}"
# shellcheck source=/dev/null
source "${ROOT}/lib/sg-paths.sh"
sg_paths_export_defaults

echo "Building Dewey catalog from field drive…"
pythong "${ROOT}/lib/h7-library-bridge.py" build --force >/dev/null

echo "Generating GitHub library tree at ${NEXUS_DEWEY_GITHUB_ROOT}…"
pythong "${ROOT}/lib/dewey-library-github.py"

echo "OK — library/dewey ready for GitHub"