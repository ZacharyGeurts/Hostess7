#!/usr/bin/env bash
# VSYNC Locker bootstrap — harden, desktop entry, background guard (idempotent).
set -euo pipefail

_LIB="$(cd "$(dirname "$0")" && pwd)"
_ROOT="$(cd "${_LIB}/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-${_ROOT}}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${NEXUS_INSTALL_ROOT}/.nexus-state}"

PY="${NEXUS_PYTHONG:-$(command -v pythong 2>/dev/null || true)}"
[[ -n "$PY" ]] || PY="$(command -v python3 2>/dev/null || true)"
LOCKER="${NEXUS_INSTALL_ROOT}/lib/field-vsync-locker.py"
[[ -f "$LOCKER" && -n "$PY" ]] || exit 0

"$PY" "$LOCKER" harden >/dev/null 2>&1 || true
"$PY" "$LOCKER" install-desktop >/dev/null 2>&1 || true
if [[ "${NEXUS_VSYNC_LOCKER_GUARD:-1}" == "1" ]]; then
  "$PY" "$LOCKER" launch >/dev/null 2>&1 || true
fi