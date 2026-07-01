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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" stack_tests "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

# Stack tests — AmmoLang assert engine (replaces 6k-line bash suite).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-state}"
export SG_ROOT="${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}"
export GROK16_ROOT="${GROK16_ROOT:-${ROOT}/Grok16}"
export PATH="${ROOT}/PythonG/bin:${PATH:-}"
export AML_BUILD="${AML_BUILD:-1}"
export AML_INLINE="${AML_INLINE:-1}"

PY="${NEXUS_PYTHONG:-pythong}"
command -v "$PY" >/dev/null 2>&1 || PY=python3

# Fresh isolated state like legacy suite
rm -rf "$NEXUS_STATE_DIR"
mkdir -p "$NEXUS_STATE_DIR"

log() { printf '[run-tests] %s\n' "$*" >&2; }

if [[ "${AML_BUILD:-1}" != "0" && -f "${ROOT}/lib/ammolang-run.sh" ]]; then
  log "AmmoLang stack_tests — assert · suite · hang guard"
  exec bash "${ROOT}/lib/ammolang-run.sh" stack_tests "$@"
fi

log "fallback — field-ammolang-test.py stack"
exec "$PY" "${ROOT}/lib/field-ammolang-test.py" stack "$@"
