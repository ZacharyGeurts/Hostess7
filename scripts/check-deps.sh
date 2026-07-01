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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/check-deps.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Hostess7 / NewLatest dependency check — fail with clear list if required tools missing.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
fail=0
warn=0

check_cmd() {
  local label="$1" cmd="$2" required="${3:-1}"
  if command -v "$cmd" >/dev/null 2>&1; then
    printf '  OK   %s (%s)\n' "$label" "$(command -v "$cmd")"
    return 0
  fi
  if [[ "$required" == "1" ]]; then
    printf '  FAIL %s — missing: %s\n' "$label" "$cmd" >&2
    fail=$((fail + 1))
  else
    printf '  WARN %s — optional missing: %s\n' "$label" "$cmd" >&2
    warn=$((warn + 1))
  fi
}

echo "=== Hostess7 dependency check ==="
echo "  root: ${ROOT}"
echo ""

check_cmd bash bash
check_cmd python3 python3
check_cmd curl curl
check_cmd git git
check_cmd rsync rsync
check_cmd sha256sum sha256sum
check_cmd find find
check_cmd "pythong (or python3)" pythong 0
check_cmd sudo sudo 0
check_cmd cmake cmake 0
check_cmd gcc gcc 0
check_cmd shellcheck shellcheck 0

if [[ ! -f "${ROOT}/lib/ammolang-run.sh" ]]; then
  echo "  FAIL ammolang-run.sh not found under ${ROOT}/lib" >&2
  fail=$((fail + 1))
fi
if [[ ! -x "${ROOT}/Hostess7/Hostess7.sh" && ! -f "${ROOT}/Hostess7/Hostess7.sh" ]]; then
  echo "  WARN Hostess7/Hostess7.sh not found — brain hub may be incomplete" >&2
  warn=$((warn + 1))
fi

echo ""
if [[ "$fail" -gt 0 ]]; then
  echo "RESULT: FAIL ($fail required missing, $warn optional)" >&2
  exit 1
fi
echo "RESULT: PASS ($warn optional missing)"
exit 0