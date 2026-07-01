# NEXUS-Shield v9.0.3 — Single version source + DNS tab wiring

**Release date:** 2026-06-24

## Version unification

All runtimes now read **`NEXUS_VERSION` from `lib/nexus-common.sh`** via `lib/nexus_version.py`:

- `threat-panel-http.py`, `hostess7-command.py`, `nexus-update.py`, `field-us-intel.py`, `target-bleed.py`
- `nexus_read_version()` helper in `nexus-common.sh` for shell callers
- Panel JS no longer stamps hardcoded `8.2.0` / `8.3.0` — version comes from `/api/status` and `paintPanel`

## DNS & DHCP tab wiring fixes

- `field-dns.py` — `dns_admin_portal` status (ports 7/77/777 probe) included in panel JSON
- `dns-dashboard.js` — prefers server `threat_model` / `traffic_patterns`; admin portal from field slice; foreign resolver fallback list
- Tab activation uses `currentPanel === "dns"`; refresh merges `lastPanelData`; `moduleReady` accepts threat/traffic fields
- Command deck + braille labels: **DNS & DHCP**

## Upgrade

```bash
./nexus.sh --no-browser
```

Open **https://127.0.0.1:9477/field** — header shows live version from `nexus-common.sh`.