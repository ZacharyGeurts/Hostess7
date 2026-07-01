# NEXUS-Shield 7.3.0 — Hostess 7 DNS Admin · Equipment Room

## DNS Admin Portal (ports 7 · 77 · 777)
- **Read-only** engineer login — DNS information only, **no remote controls**
- Tired-engineer passkeys: port number (`7`, `77`, `777`) or mnemonics (`lucky7`, `double77`, `triple7`)
- **Welcome upfront** — full DNS briefing on login so you can end the call fast
- **Equipment room reporting** — MDF/IDF checklist enabled by default when prompted
- Legacy gear interop: BIND 9, Windows Server DNS, Cisco forwarders, Pi-hole, ISP CPE
- Field DNS peers — local Truth Resolver + LAN discovery + `field-dns-peers.json`

## Policy
- Remote control paths actively **403 blocked** (firewall, attack-kit, RDP, VNC, SSH, restart)
- Firewall permits inbound TCP `{7, 77, 777}` only for this portal
- Main panel stays loopback-only on 9477

## Modules
- `lib/dns-admin-portal.py` — multi-port HTTP server
- `lib/dns-admin-portal.sh` — serve loop, firewall permit
- `lib/equipment-room-field.py` — equipment room + field server reporting
- `data/dns-admin-seed.json` — admins, passkeys, legacy gear, checklist
- `panel/assets/dns-admin-portal.html` — standalone admin UI

## Config
```
NEXUS_DNS_ADMIN_PORTAL=1
NEXUS_DNS_ADMIN_PORTS=7,77,777
```

Access: `http://<host>:7/` · `:77/` · `:777/`