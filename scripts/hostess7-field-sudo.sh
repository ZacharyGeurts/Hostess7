#!/usr/bin/env bash
# Scoped sudo wrapper — only allowlisted Hostess7 field actions (installed to /usr/local/bin).
set -euo pipefail

ROOT="${NEXUS_INSTALL_ROOT:-/home/default/Desktop/SG/NewLatest}"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
export AML_BUILD=0
PY="${PYTHON:-python3}"

usage() {
  cat <<EOF
hostess7-field-sudo — scoped elevation for humans + AI communique

  hostess7-field-sudo verify
  hostess7-field-sudo run <action>

Actions: dns-primary queen-lan truth-dns-serve dns-table-clean nexus-genius rebuild-internet
EOF
}

case "${1:-verify}" in
  -h|--help|help) usage ;;
  verify|json|status)
    exec "$PY" "$ROOT/lib/hostess7-sudo-secure.py" verify
    ;;
  run)
    exec "$PY" "$ROOT/lib/hostess7-sudo-secure.py" run "${2:?action required}"
    ;;
  *)
    echo "unknown: $1" >&2
    usage
    exit 1
    ;;
esac