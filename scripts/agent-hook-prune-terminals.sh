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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/agent-hook-prune-terminals.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Prune old Grok harness terminal logs (PreToolUse hook — no env vars in hook JSON)
set -euo pipefail
TERMINALS="/home/default/.grok/projects/home-default-Desktop-SG/terminals"
mkdir -p "$TERMINALS" 2>/dev/null || exit 0
mapfile -t _old < <(ls -1t "$TERMINALS"/*.txt 2>/dev/null | tail -n +6) || true
((${#_old[@]})) && rm -f "${_old[@]}" || true
exit 0