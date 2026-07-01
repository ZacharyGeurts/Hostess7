#!/usr/bin/env bash
# VSYNC Locker — double-click launcher; starts background guard (single instance).
set -euo pipefail

_LIB="$(cd "$(dirname "$0")" && pwd)"
_ROOT="$(cd "${_LIB}/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-${_ROOT}}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${NEXUS_INSTALL_ROOT}/.nexus-state}"

PY="${PY:-python3}"
LOCKER="${NEXUS_INSTALL_ROOT}/lib/field-vsync-locker.py"
PID_FILE="${NEXUS_STATE_DIR}/field-vsync-locker-guard.pid"
LOG="${NEXUS_STATE_DIR}/field-vsync-locker-guard.log"

mkdir -p "${NEXUS_STATE_DIR}"

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(tr -d ' \n' <"$PID_FILE" 2>/dev/null || true)"
  if [[ -n "$old_pid" ]] && kill -0 "$old_pid" 2>/dev/null; then
    exit 0
  fi
fi

nohup env \
  NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" \
  NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
  "$PY" "$LOCKER" guard --quiet >>"$LOG" 2>&1 &
disown 2>/dev/null || true
exit 0