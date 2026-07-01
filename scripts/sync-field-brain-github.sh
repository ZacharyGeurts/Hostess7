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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/sync-field-brain-github.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Ensure Hostess7 field brain + NEXUS library/dewey are present and wired for panel + GitHub.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
# shellcheck source=/dev/null
source "${ROOT}/lib/sg-paths.sh"
sg_paths_export_defaults

# shellcheck source=/dev/null
source "${ROOT}/lib/nexus-common.sh"
# shellcheck source=/dev/null
source "${ROOT}/lib/hostess7-field.sh"
# shellcheck source=/dev/null
source "${ROOT}/lib/field-brain-sync.sh"

echo "=== NEXUS field brain + library sync ==="
nexus_field_brain_sync

echo "Building Dewey GitHub tree…"
export NEXUS_DEWEY_GITHUB_ROOT="${NEXUS_DEWEY_GITHUB_ROOT:-$ROOT/library}"
if [[ -f "${ROOT}/lib/dewey-library-github.py" ]]; then
  pythong "${ROOT}/lib/h7-library-bridge.py" build --force >/dev/null
  pythong "${ROOT}/lib/dewey-library-github.py"
fi

best="$(nexus_field_brain_best_root 2>/dev/null || hostess7_field_root)"
echo "field_root: ${best}"
pythong "${ROOT}/lib/field-brain-panel.py" json | pythong -c "
import json,sys
d=json.load(sys.stdin)
print('brain_ok:', d.get('ok'))
print('manifest_count:', d.get('manifest_count'))
print('corpus_count:', d.get('corpus_count'))
print('superintel:', d.get('superintelligence',{}).get('available'))
print('github_library_books:', d.get('github_library_books'))
"
echo "OK — field brain + library wired"