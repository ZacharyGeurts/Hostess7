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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:Queen/scripts/g16-toolchain.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Queen → Grok16 delegate — unified g16 @ 16.1.1, field_opt optimizations
set -euo pipefail
QUEEN="$(cd "$(dirname "$0")/.." && pwd)"
SG="$(cd "$QUEEN/../.." && pwd)"
GROK16_ROOT="${GROK16_ROOT:-${NEXUS_INSTALL_ROOT:-$SG/NewLatest}/Grok16}"
G16_SH="$GROK16_ROOT/scripts/grok16-toolchain.sh"

if [[ -f "$G16_SH" ]]; then
  export GROK16_ROOT GROK16_QUEEN_ROOT="${GROK16_QUEEN_ROOT:-$QUEEN}"
  export G16_PREFIX="${G16_PREFIX:-$GROK16_ROOT}"
  exec bash "$G16_SH" "${@:-status}"
fi

echo "Grok16 toolchain missing at $G16_SH — set GROK16_ROOT" >&2
exit 1