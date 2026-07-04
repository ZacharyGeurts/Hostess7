#!/usr/bin/env bash
# Live terminal UI — watch field population, logical edges, DHCP/DNS grow.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
PY="${PYTHON:-python3}"

usage() {
  cat <<'EOF'
field-grow-watch.sh — live terminal grow dashboard

  ./scripts/field-grow-watch.sh          curses TUI (q quit)
  ./scripts/field-grow-watch.sh once     one-shot JSON snapshot
  ./scripts/field-grow-watch.sh bash     loop print every 2s (plain bash)
  ./scripts/field-grow-watch.sh rescue   run rescue ingress then watch

Environment:
  NEXUS_FIELD_GROW_API=http://127.0.0.1:9477/api/field-grow-watch
EOF
}

cmd_bash_loop() {
  while true; do
    clear
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  FIELD GROW WATCH — inside field · logical edges · all IPs   ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    "$PY" "$ROOT/lib/field-grow-watch.py" once 2>/dev/null | "$PY" -c "
import json,sys
d=json.load(sys.stdin)
keys=[
 ('Population', d.get('population')),
 ('Devices', d.get('devices')),
 ('Logical edges', d.get('logical_edges')),
 ('Logical shards', d.get('logical_shards')),
 ('Planet DHCP', d.get('planet_dhcp')),
 ('Planet DNS', d.get('planet_dns')),
 ('Local leases', d.get('local_dhcp_leases')),
 ('Pool slots', d.get('dhcp_pool_slots')),
 ('Quarantined', d.get('quarantined')),
 ('Everyone', d.get('everyone_total')),
 ('Ingress', d.get('ingress_policy')),
]
for k,v in keys:
    print(f'  {k:<18} {v}')
print()
print('  Ctrl+C quit · ./scripts/field-grow-watch.sh for full TUI')
"
    sleep 2
  done
}

main() {
  local cmd="${1:-tui}"
  case "$cmd" in
    -h|--help|help) usage ;;
    once|json|api) exec "$PY" "$ROOT/lib/field-grow-watch.py" once ;;
    bash|loop) cmd_bash_loop ;;
    rescue)
      "$PY" "$ROOT/lib/field-rescue-ingress.py" rescue >/dev/null 2>&1 || true
      exec "$PY" "$ROOT/lib/field-grow-watch.py"
      ;;
    tui|curses|"") exec "$PY" "$ROOT/lib/field-grow-watch.py" ;;
    *) echo "unknown: $cmd" >&2; usage; exit 1 ;;
  esac
}

main "$@"