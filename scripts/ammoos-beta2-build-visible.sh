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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/ammoos-beta2-build-visible.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Full AmmoOS 2.0.0-beta build — all phases visible in terminal + log file.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="${ROOT}/dist/ammoos-beta2-build.log"
VER="2.0.0-beta"

export SG_ROOT="${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}"
export AMMOOS_VERSION="${VER}"
# SUDO_PASS only when explicitly set — never hardcoded; sudo prompts if needed.

mkdir -p "${ROOT}/dist"

{
  echo "[$(date '+%H:%M:%S')] === AmmoOS ${VER} full build (beta 2) ==="
  echo "log: ${LOG}"
  echo "tree: ${ROOT}"

  if [[ -f "${HOME}/.config/sg/github-mcp.env" ]]; then
    # shellcheck source=/dev/null
    set -a && source "${HOME}/.config/sg/github-mcp.env" && set +a
    export GH_TOKEN="${GITHUB_MCP_TOKEN:-${GH_TOKEN:-}}"
    echo "[$(date '+%H:%M:%S')] auth: MCP secure (github-mcp.env)"
  fi

  exec bash "${ROOT}/scripts/ammoos-release.sh" --version "${VER}" --push
} 2>&1 | tee "${LOG}"