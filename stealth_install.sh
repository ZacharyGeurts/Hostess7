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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:stealth_install.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Deprecated — use install-all.sh (single installer).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    powershell.exe -ExecutionPolicy Bypass -File "${ROOT}/stealth.ps1"
    ;;
  *)
    exec bash "${ROOT}/install-all.sh" "$@"
    ;;
esac