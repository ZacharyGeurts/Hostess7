# NEXUS-Shield 7.4.0 — Local DNS Capture · Multipoint Secure ID

## Every local DNS request → NEXUS Truth
- Bind **127.0.0.1**, **127.0.0.53** (stub override), and **::1** on port 53
- **Override user DNS settings** — `/etc/resolv.conf` steered to loopback; symlink broken when needed
- Re-enforced every vigil cycle (300s default) — settings cannot drift back to foreign DNS

## Never add untrusted
- Foreign resolver egress blocked (Google, Cloudflare, Charter, Quad9) on UDP/TCP 53
- DoT port 853 egress blocked
- Multipoint registry only lists **trusted** identification points with secure fingerprints

## Multipoint secure identification
- `lib/dns-multipoint-identity.py` — SHA-256 fingerprints per listener (hostname + manifest + tier)
- Field DNS peers from `field-dns-peers.json` only when explicitly trusted
- Panel DNS tab shows identification points table + override status

## Config
```
NEXUS_FIELD_DNS_LOCAL_CAPTURE=1
NEXUS_FIELD_DNS_BREAK_RESOLV_SYMLINK=1
NEXUS_FIELD_DNS_BINDS_IPV4=127.0.0.1,127.0.0.53
NEXUS_FIELD_DNS_BINDS_IPV6=::1
```

## Version policy (from 7.4.0 onward)
Every update bumps **full minor** (7.4.0 → 7.5.0) with `RELEASE-X.Y.0.md` + `./scripts/release.sh`.