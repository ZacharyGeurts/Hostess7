#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/znetwork-wireless-fcc.py" ]]
  grep -q 'wireless_fcc' "${ROOT}/data/znetwork-doctrine.json"
  grep -q 'trace_action_behind' "${ROOT}/lib/znetwork-wireless-fcc.py"
  grep -q 'strike_action_behind' "${ROOT}/lib/znetwork-wireless-fcc.py"
  grep -q 'fix_not_kill' "${ROOT}/data/znetwork-doctrine.json"
  grep -q 'nexus_znetwork_wireless_fcc_bind_and_scan' "${ROOT}/lib/znetwork-field.sh"
  grep -q '_is_own_router' "${ROOT}/lib/field-rf-sentinel.py"
  grep -q 'fix_router_strike_actor' "${ROOT}/lib/znetwork-relayer.py"
  tmp_state="$(mktemp -d)"
  printf '{"schema":"znetwork-own-router/v1","bound":true,"gateway_ip":"192.168.1.1","bssid":"aa:bb:cc:dd:ee:ff","ssid":"HomeNet"}\n' \
    >"${tmp_state}/znetwork-own-router.json"
out=$("$PY" "${ROOT}/lib/znetwork-wireless-fcc.py" json 2>/dev/null || true); grep -q '"schema": "znetwork-wireless-fcc/v1"'
out=$("$PY" "${ROOT}/lib/znetwork-wireless-fcc.py" is-own 192.168.1.1 2>/dev/null || true); grep -q '"own": true'
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" \
    "$PY" -c "
import json, os, sys
sys.path.insert(0, '${ROOT}/lib')
os.environ['NEXUS_INSTALL_ROOT'] = '${ROOT}'
os.environ['NEXUS_STATE_DIR'] = '${tmp_state}'
import importlib.util
spec = importlib.util.spec_from_file_location('zwf', '${ROOT}/lib/znetwork-wireless-fcc.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
tr = mod.trace_action_behind({'kind':'hostile_gateway_symptom','ip':'192.168.1.1'})
assert tr.get('symptom_is_own_router') is True
assert tr.get('policy') in ('fix_router_only','fix_router_strike_actor')
print('trace_ok')
"
  rm -rf "$tmp_state"
