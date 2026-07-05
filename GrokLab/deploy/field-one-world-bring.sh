#!/usr/bin/env bash
# Field 1 worldwide bring — test secure stack, rollout batch, optional double.
set -euo pipefail
ROOT="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
STATE="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
PY="${PY:-$(command -v pythong || command -v python3)}"
export NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$STATE"
export NEXUS_FIELD_DHCP_FOREIGN_PROBE=0
export NEXUS_FIELD_COLLISION_SOFT_INGRESS=1

CMD="${1:-test}"
shift || true

case "$CMD" in
  test)
    exec "$PY" "$ROOT/lib/field-one-rollout.py" test "$@"
    ;;
  rollout|roll|wave)
    exec "$PY" "$ROOT/lib/field-one-rollout.py" rollout "$@"
    ;;
  double|double-worldwide)
    exec "$PY" "$ROOT/lib/field-one-rollout.py" double "$@"
    ;;
  absorb)
    exec "$PY" "$ROOT/lib/field-one.py" absorb "$@"
    ;;
  *)
    exec "$PY" "$ROOT/lib/field-one-rollout.py" "${CMD}" "$@"
    ;;
esac