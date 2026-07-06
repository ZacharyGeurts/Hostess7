#!/usr/bin/env bash
# Field watch DHCP — observe foreign DHCP; not our DHCP server.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
PY="${PYTHON:-python3}"

usage() {
  cat <<'EOF'
field-watch-dhcp.sh — observe-only DHCP witness (not field-dhcp serve)

  ./scripts/field-watch-dhcp.sh ensure   start automated watcher if down
  ./scripts/field-watch-dhcp.sh once     one-shot observe JSON
  ./scripts/field-watch-dhcp.sh serve    foreground poll loop
  ./scripts/field-watch-dhcp.sh stop     stop watcher
  ./scripts/field-watch-dhcp.sh json     cached panel

API: /api/field-watch-dhcp · panel: /field-watch-dhcp
EOF
}

main() {
  local cmd="${1:-ensure}"
  case "$cmd" in
    -h|--help|help) usage ;;
    once|observe|build) exec "$PY" "$ROOT/lib/field-watch-dhcp.py" once ;;
    json|panel|status) exec "$PY" "$ROOT/lib/field-watch-dhcp.py" json ;;
    serve) exec "$PY" "$ROOT/lib/field-watch-dhcp.py" serve ;;
    stop) exec "$PY" "$ROOT/lib/field-watch-dhcp.py" stop ;;
    ensure|auto|start|"") exec "$PY" "$ROOT/lib/field-watch-dhcp.py" ensure ;;
    why) exec "$PY" "$ROOT/lib/field-watch-dhcp.py" why ;;
    *) echo "unknown: $cmd" >&2; usage; exit 1 ;;
  esac
}

main "$@"