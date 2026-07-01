# NEXUS-Shield v9.0.2 — Planetary DNS & DHCP command tab

**Release date:** 2026-06-24

## DNS & DHCP tab cleanup

One professional tab for planetary DNS and DHCP management:

- **Threat levels & active concerns** — posture strip, overall risk gauge, engineer alerts
- **Traffic patterns** — DNS query/cache/block/error bands plus DHCP lease activity
- **Secure threat model** — STRIDE + DNS/DHCP vectors with RFC controls and mitigation status
- **Details** — operations (takeover, egress, threat guard, multipoint), internet field, planetary zones, RFC/legal/roots/legacy, admin portal

### Changes

- `panel/threat-panel.html` — consolidated DNS & DHCP tab layout; nav label **DNS & DHCP**
- `panel/assets/dns-dashboard.js` — unified renderers: posture, traffic, threat model, operations detail
- `panel/assets/dusty-midnight.css` — planetary command grid, threat levels, traffic bars
- `lib/field-dns.py` — `traffic_patterns` and `threat_model` in panel JSON

## Upgrade

```bash
./nexus.sh --no-browser
```

Open **https://127.0.0.1:9477/field** → **DNS & DHCP** tab.

Includes v9.0.1 TLS fix and all v9.0.0 wartime / neural / truth-rating features.