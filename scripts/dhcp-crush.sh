#!/usr/bin/env bash
# DHCP crush — Queen LAN up, takeover primary, prove OFFER, refresh panel.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
export NEXUS_FIELD_DHCP="${NEXUS_FIELD_DHCP:-1}"
export NEXUS_FIELD_DHCP_BIND="${NEXUS_FIELD_DHCP_BIND:-192.168.47.1}"

PGREP="${PGREP:-/usr/bin/pgrep}"

bash "${ROOT}/scripts/queen-lan-up.sh" >&2 2>&1 || true

if ! "$PGREP" -f 'field-dhcp.py serve' >/dev/null 2>&1; then
  nohup env NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
    NEXUS_FIELD_DHCP="$NEXUS_FIELD_DHCP" NEXUS_FIELD_DHCP_BIND="$NEXUS_FIELD_DHCP_BIND" \
    python3 "${ROOT}/lib/field-dhcp.py" serve \
    >>"${NEXUS_STATE_DIR}/field-dhcp-serve.log" 2>&1 &
  sleep 1
fi

json="$(NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
  python3 "${ROOT}/lib/field-dhcp.py" crush)"

python3 -c "
import json, sys
d = json.loads(sys.argv[1])
c = d.get('crush') or {}
print('DHCP crushing:', d.get('running'), '| bind:', d.get('bind'))
print('OFFER queen:', c.get('offer_queen'), '| loopback:', c.get('offer_loopback'))
print('takeover:', d.get('takeover_phase'), '| may_serve:', d.get('may_serve'))
" "$json"

NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
  python3 "${ROOT}/lib/field-dns-dhcp-collision-guard.py" enforce \
  > "${NEXUS_STATE_DIR}/field-dns-dhcp-collision-guard-enforce.json" 2>/dev/null || true
python3 -c "
import json
from pathlib import Path
p = Path('${NEXUS_STATE_DIR}/field-dns-dhcp-collision-guard-enforce.json')
if p.is_file():
    d = json.loads(p.read_text())
    s = d.get('sole_authority') or {}
    print('SOLE authority:', s.get('ok'), '| collisions:', d.get('collision_count', 0))
    print('Foreign threats:', d.get('foreign_threat_count', 0), '| eradicated:', (d.get('enforce') or {}).get('threats_eradicated', 0))
" 2>/dev/null || true

NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
  python3 "${ROOT}/lib/field-planetary-dns-dhcp.py" panel \
  > "${ROOT}/Hostess7/docs/api/field-planetary-dns-dhcp.json" 2>/dev/null || true
python3 -c "
import json
from pathlib import Path
p = Path('${ROOT}/Hostess7/docs/api/field-planetary-dns-dhcp.json')
if p.is_file():
    d = json.loads(p.read_text())
    c = d.get('counts') or {}
    print('PLANET DHCP:', c.get('planet_dhcp_total'), '| DNS:', c.get('planet_dns_total'), '| total:', c.get('planet_lease_total'))
" 2>/dev/null || true

NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$NEXUS_INSTALL_ROOT" \
  python3 "${ROOT}/lib/field-botnet-dns-dhcp.py" panel \
  > "${ROOT}/Hostess7/docs/api/field-botnet-dns-dhcp.json" 2>/dev/null || true