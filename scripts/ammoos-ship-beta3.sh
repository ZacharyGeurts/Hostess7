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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/ammoos-ship-beta3.sh" "$@"
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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" ship "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

# AmmoOS 2.0.0-beta3 ship — AmmoLang with minute progress posts.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export SG_ROOT="${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}"
export GROK16_ROOT="${GROK16_ROOT:-${SG_ROOT}/Grok16}"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
export AMMOOS_VERSION="${AMMOOS_VERSION:-2.0.0-beta3}"
export AML_BUILD=1
export AML_FAST=1
export AML_PROGRESS=1
export AML_PROGRESS_MIN=60
export AML_GITHUB_TRANSPORT=mcp_secure
export HOSTESS_TRUTH_FLOOR="${HOSTESS_TRUTH_FLOOR:-58}"
export SKIP_BETA_PIPELINE="${SKIP_BETA_PIPELINE:-1}"

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }

log "AmmoLang ship beta3 — progress every 60s"
log "panel: ${NEXUS_STATE_DIR}/ammolang-release-progress.json"
log "tail:  tail -f ${NEXUS_STATE_DIR}/field-ammolang-build.log"

exec bash "${ROOT}/lib/ammolang-run.sh" ship "$@"
