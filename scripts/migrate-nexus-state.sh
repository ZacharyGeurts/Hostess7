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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/migrate-nexus-state.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Move repo-local .nexus-state to runtime dir — state is ephemeral, never committed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=/dev/null
source "${ROOT}/lib/nexus-common.sh"
nexus_init_runtime_paths

REPO_STATE="${ROOT}/.nexus-state"
TARGET="${NEXUS_STATE_DIR}"

if [[ ! -d "$REPO_STATE" ]]; then
  exit 0
fi

if [[ "$TARGET" == "$REPO_STATE" ]]; then
  echo "migrate-nexus-state: already using repo-local state (${REPO_STATE})" >&2
  exit 0
fi

if [[ -d "$TARGET" ]] && [[ -n "$(ls -A "$TARGET" 2>/dev/null || true)" ]]; then
  echo "migrate-nexus-state: target ${TARGET} already has data — leaving ${REPO_STATE} in place." >&2
  echo "  Remove ${REPO_STATE} manually after backup if you want a clean tree." >&2
  exit 0
fi

echo "migrate-nexus-state: moving ${REPO_STATE} → ${TARGET}" >&2
mkdir -p "$TARGET"
if command -v rsync >/dev/null 2>&1; then
  rsync -a "${REPO_STATE}/" "${TARGET}/"
else
  cp -a "${REPO_STATE}/." "${TARGET}/"
fi
echo "migrate-nexus-state: done. Add ${REPO_STATE} to git clean if still tracked." >&2