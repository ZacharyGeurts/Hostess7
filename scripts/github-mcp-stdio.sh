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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/github-mcp-stdio.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Private ZacharyGeurts GitHub MCP — local stdio, token from ~/.config/sg/github-mcp.env
set -euo pipefail
ENV="${HOME}/.config/sg/github-mcp.env"
BIN="${HOME}/.local/bin/github-mcp-server"
if [[ ! -x "${BIN}" ]]; then
  echo "github-mcp-server missing: run scripts/github-mcp-private-setup.sh" >&2
  exit 1
fi
if [[ ! -f "${ENV}" ]]; then
  echo "missing ${ENV} — run scripts/github-mcp-private-setup.sh" >&2
  exit 1
fi
# shellcheck disable=SC1090
source "${ENV}"

export GITHUB_PERSONAL_ACCESS_TOKEN="${GITHUB_MCP_TOKEN:?GITHUB_MCP_TOKEN unset in ${ENV}}"
export GITHUB_TOOLSETS="${GITHUB_MCP_TOOLSETS:-repos,pull_requests}"

readonly_flag=()
if [[ "${1:-}" == "read" ]]; then
  readonly_flag=(--read-only)
fi

exec "${BIN}" stdio "${readonly_flag[@]}"