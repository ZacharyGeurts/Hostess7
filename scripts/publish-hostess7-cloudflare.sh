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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/publish-hostess7-cloudflare.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Publish Hostess7 web → GitHub Pages, then refresh Cloudflare edge Worker proxy.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOSTESS7_VERSION="${HOSTESS7_VERSION:-1.0.0-beta}"
WORKER_NAME="${CF_HOSTESS7_WORKER:-hostess7}"

log() { printf '[hostess7-cloudflare] %s\n' "$*"; }

log "step 1 — GitHub Pages (Talk & Draw)"
bash "${ROOT}/scripts/publish-hostess7-pages.sh"

log "step 2 — Cloudflare Worker edge proxy (optional; needs CF API token)"
PY="${ROOT}/lib/publish-hostess7-cloudflare.py"
if [[ -f "$PY" ]]; then
  python3 "$PY" --worker "$WORKER_NAME" --version "$HOSTESS7_VERSION" || log "WARN Cloudflare deploy partial — GitHub Pages is canonical"
else
  log "skip worker deploy (missing ${PY})"
fi

log "canonical → https://zacharygeurts.github.io/Hostess7/"
log "edge (when deployed) → https://${WORKER_NAME}.gzac5314.workers.dev/"