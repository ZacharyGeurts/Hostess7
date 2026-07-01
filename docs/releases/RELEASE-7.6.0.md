# NEXUS-Shield 7.6.0 — Graceful DNS/DHCP Takeover · Egress Integrity · LAN on US

## DNS/DHCP hardening

- **Graceful takeover** (`dns-service-takeover.py`) — NEXUS observes incumbent DNS/DHCP on arrival; never interrupts `resolv.conf` or port 67 until Truth Resolver is healthy and phase reaches **primary**.
- **Egress integrity** — permitted DNS egress verified with payload hash logging; mismatches flagged for threat eradication.
- **Threat guard** — listen-before-reject, DDoS rate limits both directions, permanent blocks with autosanitize hooks.
- **Field DHCP** — issues leases with DNS option 6 → `127.0.0.1`; serves only after takeover permits.
- **Hostess 7** — DNS inside (loopback resolver + LAN DHCP) and outside (admin ports 7/77/777 read-only) with no lateral movement.

## Panel

- **DNS tab** — NEXUS DNS + DHCP server table, takeover phase, egress integrity, threat guard panels.
- **US tab** — local network card from ARP, DHCP, home protector, equipment room, gatekeeper tables.

## Field radio / antenna (7.5 carry-forward)

- OTA catch at 83.1 MHz via field antenna; FCC master record on every lookup.

Install: `sudo ./stealth_install.sh` from source tree.  
Panel: https://127.0.0.1:9477/field