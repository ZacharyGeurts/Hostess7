#!/usr/bin/env bash
# Truth DNS serve — loopback-first; wildcard only when bind succeeds.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
export NEXUS_FIELD_DNS="${NEXUS_FIELD_DNS:-1}"
export NEXUS_FIELD_DNS_BINDS_IPV4="${NEXUS_FIELD_DNS_BINDS_IPV4:-127.0.0.1}"
export NEXUS_FIELD_DNS_BINDS_IPV6="${NEXUS_FIELD_DNS_BINDS_IPV6:-::1}"
if [[ "${NEXUS_FIELD_DNS_ANY_IP:-0}" != "1" ]]; then
  export NEXUS_FIELD_DNS_ANY_IP=0
fi
exec "${PYTHON:-python3}" "${ROOT}/lib/field-dns.py" serve