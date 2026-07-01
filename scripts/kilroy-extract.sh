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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/kilroy-extract.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Lift KILROY out of SG bundle → top-level sibling (Desktop/KILROY). Non-destructive symlink option.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SG="$(cd "${ROOT}/.." && pwd)"
SRC="${SRC:-${SG}/KILROY}"
DEST="${DEST:-$(cd "${SG}/.." && pwd)/KILROY}"
MODE="${1:-symlink}"

case "$MODE" in
  --help|-h)
    cat <<EOF
KILROY canonical placement — out of SG, never in Queen

  ./scripts/kilroy-extract.sh symlink   # Desktop/KILROY → SG/KILROY (default, safe)
  ./scripts/kilroy-extract.sh move      # physically mv SG/KILROY → ../KILROY
  ./scripts/kilroy-extract.sh status    # show resolved path

After: export KILROY_ROOT=\$(./lib/kilroy-resolve.sh)
EOF
    exit 0
    ;;
  status)
    # shellcheck source=/dev/null
    source "${ROOT}/lib/kilroy-resolve.sh"
    nexus_kilroy_export "$SG" && echo "KILROY_ROOT=${KILROY_ROOT}"
    exit 0
    ;;
  move)
    if [[ ! -d "$SRC" ]]; then
      echo "Source missing: $SRC" >&2
      exit 1
    fi
    if [[ -e "$DEST" ]]; then
      echo "Destination exists: $DEST (refuse overwrite)" >&2
      exit 1
    fi
    mv "$SRC" "$DEST"
    echo "Moved: $SRC → $DEST"
    ;;
  symlink|*)
    if [[ ! -d "$SRC" ]]; then
      echo "Source missing: $SRC" >&2
      exit 1
    fi
    if [[ -L "$DEST" ]]; then
      rm -f "$DEST"
    elif [[ -e "$DEST" && ! -d "$DEST" ]]; then
      echo "Blocker: $DEST exists and is not a symlink" >&2
      exit 1
    elif [[ -d "$DEST" && ! -L "$DEST" ]]; then
      echo "KILROY already at $DEST (directory)" >&2
      exit 0
    fi
    ln -sfn "$SRC" "$DEST"
    echo "Symlink: $DEST → $SRC"
    ;;
esac

# shellcheck source=/dev/null
source "${ROOT}/lib/kilroy-resolve.sh"
nexus_kilroy_export "$SG" && echo "Resolved KILROY_ROOT=${KILROY_ROOT}"