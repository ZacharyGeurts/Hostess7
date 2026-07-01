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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/github-mcp-private-setup.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Private GitHub MCP for ZacharyGeurts — local binary + gh token, no Copilot OAuth.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BIN="${HOME}/.local/bin/github-mcp-server"
ENV="${HOME}/.config/sg/github-mcp.env"
VERSION="${GITHUB_MCP_VERSION:-v1.5.0}"
ARCHIVE="github-mcp-server_Linux_x86_64.tar.gz"
URL="https://github.com/github/github-mcp-server/releases/download/${VERSION}/${ARCHIVE}"

echo "==> Private GitHub MCP (ZacharyGeurts only)"
mkdir -p "${HOME}/.local/bin" "${HOME}/.config/sg"

if [[ ! -x "${BIN}" ]]; then
  echo "==> Installing github-mcp-server ${VERSION}"
  tmp="$(mktemp)"
  curl -fsSL -o "${tmp}" "${URL}"
  tar -xzf "${tmp}" -C "${HOME}/.local/bin"
  chmod +x "${BIN}"
  rm -f "${tmp}"
fi
"${BIN}" --version

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI required. Install: https://cli.github.com/" >&2
  exit 1
fi
if ! gh api user --jq .login >/dev/null 2>&1; then
  echo "==> gh not authed — run: gh auth login -h github.com -p https -w"
  gh auth login -h github.com -p https -w --skip-ssh-key
fi
LOGIN="$(gh api user --jq .login)"
if [[ "${LOGIN}" != "ZacharyGeurts" ]]; then
  echo "WARN: gh login is ${LOGIN}, expected ZacharyGeurts" >&2
fi

umask 077
TOKEN="$(gh auth token -h github.com)"
cat >"${ENV}" <<EOF
# Private GitHub MCP — mode 600, never commit
GITHUB_MCP_TOKEN=${TOKEN}
GITHUB_MCP_TOOLSETS=repos,pull_requests
GITHUB_MCP_OWNER=ZacharyGeurts
EOF
chmod 600 "${ENV}"
echo "==> Wrote ${ENV} (repos + pull_requests toolsets)"

chmod +x "${ROOT}/scripts/github-mcp-stdio.sh"

cd "${ROOT}"
echo "==> grok mcp list"
grok mcp list
echo "==> grok mcp doctor grok_com_github"
grok mcp doctor grok_com_github || true
echo
echo "Ready. Agents in ${ROOT} use MCP server grok_com_github (local, scoped)."
echo "Refresh token after gh re-login: ./scripts/github-mcp-private-setup.sh"