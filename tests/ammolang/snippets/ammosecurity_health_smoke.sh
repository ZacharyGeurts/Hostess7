#!/usr/bin/env bash
set -euo pipefail
ROOT="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "$0")/../../.." && pwd)}"
export NEXUS_INSTALL_ROOT="$ROOT"
export AMMO_STATE_DIR="${AMMO_STATE_DIR:-$ROOT/.ammo-state-ci}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state-ci}"
mkdir -p "$AMMO_STATE_DIR" "$NEXUS_STATE_DIR"

AMMO="$ROOT/ammosecurity"
for f in lib/common.sh modules/sg_net_harden.sh modules/ammo_watch.sh modules/interface_guard.sh; do
  test -f "$AMMO/$f"
  bash -n "$AMMO/$f"
done

bash "$AMMO/modules/sg_net_harden.sh" dry-run
bash "$AMMO/modules/sg_service_cleaner.sh" status
bash "$AMMO/modules/interface_guard.sh" dry-run
bash "$AMMO/modules/ammo_watch.sh" once
python3 "$ROOT/lib/ammo-net-health.py" json | grep -q 'ammo-net-health/v1'
grep -q 'ammo-net-health' "$ROOT/lib/threat-panel-http.py"
echo "ammosecurity_health_smoke=ok"