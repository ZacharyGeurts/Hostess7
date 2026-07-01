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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/field-h7e-extract.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Double-click / xdg-open lane — H7e (or legacy H7) folder archive → extract beside the file.
set -euo pipefail

ARCHIVE="${1:?usage: field-h7e-extract.sh /path/to/archive.h7e [dest_dir]}"
DEST="${2:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export FIELD_TECH_NO_FIELD=1
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"

ARCHIVE="$(readlink -f "$ARCHIVE")"
if [[ -z "$DEST" ]]; then
  DEST="$(dirname "$ARCHIVE")"
else
  DEST="$(mkdir -p "$DEST" && cd "$DEST" && pwd)"
fi

python3 "${ROOT}/lib/field-h7-format.py" extract "$ARCHIVE" "$DEST"