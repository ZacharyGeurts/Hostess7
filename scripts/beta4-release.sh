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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/beta4-release.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Beta 4 full release — named AML route (monitored · no exec-script hang)
_ROOT_EARLY="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$_ROOT_EARLY}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$_ROOT_EARLY/.nexus-state}"

# Operator hold — checked before any AML redirect
if [[ "${BETA4_FORCE_RELEASE:-}" != "1" ]]; then
  _HOLD_RC=0
  _HOLD_JSON="$(python3 "$_ROOT_EARLY/lib/field-beta4-ready.py" hold_status 2>/dev/null)" || _HOLD_RC=$?
  if [[ "$_HOLD_RC" -eq 2 ]]; then
    echo "beta4-release: HELD — clear with: python3 lib/field-beta4-ready.py resume" >&2
    echo "$_HOLD_JSON" >&2
    exit 2
  fi
fi

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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" beta4_release "${@}"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
export HOSTESS7_TRUTH_LIE_SKIP_NEXUS=1
exec bash "$ROOT/lib/ammolang-run.sh" beta4_release "${@}"