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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:Queen/scripts/run-benchmark.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Queen Speedometer lane — benchmark mode on, Queen Field Engine when available.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INSTALL="$(cd "${ROOT}/.." && pwd)"
SG="$(cd "${INSTALL}/.." && pwd)"
PORT="${QUEEN_WORLD_PORT:-9481}"
PANEL_PORT="${NEXUS_THREAT_PANEL_PORT:-9477}"
BENCH_URL="${QUEEN_BENCH_URL:-https://browserbench.org/Speedometer3.0/}"

export SG_ROOT="${SG_ROOT:-${SG}}"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-${INSTALL}}"
export QUEEN_ROOT="${QUEEN_ROOT:-${ROOT}}"
export QUEEN_BENCHMARK_MODE=1
export QUEEN_ALLOW_EXTERNAL_URLS=1
export QUEEN_FAST_STATUS=1
export QUEEN_STATUS_CACHE_SEC=30
export NEXUS_FIELD_THERMAL_GUARD=0
export QUEEN_BROWSER_START="${QUEEN_BROWSER_START:-http://127.0.0.1:${PORT}/world/bench/}"
export QUEEN_BROWSER_HOME="${QUEEN_BROWSER_HOME:-http://127.0.0.1:${PORT}/world/bench/}"

# Ensure Queen world is up
if ! curl -sf --max-time 2 "http://127.0.0.1:${PORT}/api/queen-browser" >/dev/null 2>&1; then
  echo "Starting Queen world on :${PORT} (benchmark mode)…" >&2
  QUEEN_BENCHMARK_MODE=1 QUEEN_INLINE_BROWSER=1 "${ROOT}/scripts/run-queen.sh" --world-only 2>/dev/null &
  for _ in $(seq 1 40); do
    curl -sf --max-time 1 "http://127.0.0.1:${PORT}/api/queen-browser" >/dev/null 2>&1 && break
    sleep 0.25
  done
fi

ENGINE_LAUNCHER="${ROOT}/field-gecko/bin/launch-field-gecko.sh"
if [[ -x "${ENGINE_LAUNCHER}" ]]; then
  echo "Queen benchmark · Field Engine → ${BENCH_URL}" >&2
  exec "${ENGINE_LAUNCHER}" "${BENCH_URL}"
fi

WEB_SHELL="http://127.0.0.1:${PORT}/world/browser.html?benchmark=1"
echo "Queen benchmark · web shell → ${WEB_SHELL}" >&2
OPEN_PY="${NEXUS_INSTALL_ROOT:-${ROOT}/..}/lib/field-queen-browser-open.py"
if [[ -f "${OPEN_PY}" ]]; then
  exec env \
    NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-${ROOT}/..}" \
    QUEEN_ROOT="${ROOT}" \
    QUEEN_BROWSER_URL="${WEB_SHELL}" \
    QUEEN_NO_OS_BROWSER=1 \
    "${PY:-pythong}" "${OPEN_PY}" open
fi
exec curl -sf "${WEB_SHELL}" >/dev/null