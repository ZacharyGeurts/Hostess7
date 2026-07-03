#!/usr/bin/env bash
# Legacy open + secured — promote Truth DNS + Field DHCP to primary (Dreamcast modem welcome).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
export NEXUS_LEGACY_OPEN_SECURED=1
export NEXUS_FIELD_DNS_LEGACY_COMPAT=1
PY="${PYTHON:-python3}"
exec "$PY" "$ROOT/lib/field-legacy-connect.py" ensure-primary