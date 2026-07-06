#!/usr/bin/env bash
# Fix DNS and DHCP everywhere — prune pile-up, recover hung resolver, promote primary.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
export NEXUS_LEGACY_OPEN_SECURED="${NEXUS_LEGACY_OPEN_SECURED:-1}"
export NEXUS_FIELD_DNS="${NEXUS_FIELD_DNS:-1}"
export NEXUS_FIELD_DHCP="${NEXUS_FIELD_DHCP:-1}"
export NEXUS_NEVER_DOWN_INLINE="${NEXUS_NEVER_DOWN_INLINE:-0}"

PY="${PYTHON:-python3}"

exec "$PY" "${ROOT}/lib/field-dns-dhcp-fix.py" fix