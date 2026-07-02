#!/usr/bin/env bash
# Canonical Hostess7 version — single source via src/hostess7/__init__.py
# Usage:
#   source scripts/hostess7-version.sh
#   scripts/hostess7-version.sh bump 2.0.7h
set -euo pipefail

_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
_INIT="${_ROOT}/src/hostess7/__init__.py"

_read_version() {
  python3 -c "import sys; sys.path.insert(0,'${_ROOT}/src'); import hostess7; print(hostess7.__version__)" 2>/dev/null \
    || grep -m1 '^version = ' "${_ROOT}/pyproject.toml" | sed 's/.*"\(.*\)".*/\1/'
}

_bump_version() {
  local ver="$1"
  python3 - <<PY
from pathlib import Path
import re
init = Path("${_INIT}")
text = init.read_text(encoding="utf-8")
text = re.sub(r'__version__\s*=\s*["\'][^"\']+["\']', f'__version__ = "${ver}"', text, count=1)
init.write_text(text, encoding="utf-8")
print("${ver}")
PY
  python3 "${_ROOT}/scripts/hostess7-sync-version.py"
}

case "${1:-}" in
  bump)
    [[ -n "${2:-}" ]] || { echo "usage: hostess7-version.sh bump <version>" >&2; exit 1; }
    _bump_version "$2"
    ;;
  "")
    if [[ -z "${HOSTESS7_VERSION:-}" ]]; then
      HOSTESS7_VERSION="$(_read_version)"
    fi
    export HOSTESS7_VERSION
    export HOSTESS7_TAG="v${HOSTESS7_VERSION}"
    ;;
  *)
    echo "usage: hostess7-version.sh [bump VERSION]" >&2
    exit 1
    ;;
esac