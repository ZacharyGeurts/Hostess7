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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/ammoos-unpack-source.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Unpack AmmoOS source release (.h7e extractable archive, or legacy .h7).
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ammooos-unpack-source.sh <ammoos-VERSION-source.h7e|.h7> [dest_dir]

  H7e/H7 release archive → extract tree into dest_dir (default: cwd).
EOF
}

[[ $# -ge 1 ]] || { usage >&2; exit 1; }
[[ "${1:-}" != "-h" && "${1:-}" != "--help" ]] || { usage; exit 0; }

ARCHIVE="$(readlink -f "$1")"
[[ -f "$ARCHIVE" ]] || { echo "missing archive: $ARCHIVE" >&2; exit 1; }

DEST="${2:-.}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export FIELD_TECH_NO_FIELD=1
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"

python3 "${ROOT}/lib/field-h7-format.py" extract "$ARCHIVE" "$(mkdir -p "$DEST" && cd "$DEST" && pwd)"
TOP="$(find "$DEST" -maxdepth 1 -type d -name 'ammoos-*' | head -1)"
if [[ -n "$TOP" ]]; then
  echo "extracted: $TOP"
else
  echo "extracted under: $DEST"
fi