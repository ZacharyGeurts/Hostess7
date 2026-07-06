#!/usr/bin/env bash
# Field root status — SSH/telnet safe read-only command (no PID spawn).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
PY="${PYTHON:-python3}"
FMT="${1:-telnet}"
exec "$PY" "${ROOT}/lib/field-root-status.py" "${FMT}"