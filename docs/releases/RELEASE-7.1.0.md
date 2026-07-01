# NEXUS-Shield 7.1.0 — Dusty Midnight · Hostess Profile

## Dusty Midnight theme
- **`panel/assets/dusty-midnight.css`** — warm dusty blues, 1.18× UI scale, bigger tabs/buttons/dropdowns, scroll-friendly layouts
- Panel header: **NEXUS-Shield v7.1.0 · Hostess 7 · Dusty Midnight**

## Secure profile defaults
- Fresh installs and `nexus_settings_apply_consumer_defaults` now turn **ON** every hardening toggle: shadow, entropy, privacy, paranoia block, firewall auto-block, autosanitize, adblock, Hostess7 corroborate
- `NEXUS_NETWORK_LOCKDOWN` stays **OFF** (file sharing friendly)

## EXTREME security — 4★ and 5★ hosts
- **`lib/host-security-tier.py`** — EXTREME envelope on every protection point for 4★/5★ hosts
- Honorability 4★/5★ domains tagged `protection_level: extreme` on live connections
- Complete US profile (name + address + URLs) → auto-applies **EXTREME** watchers; adblock stays **relaxed (fair)** for 4★/5★ hosts
- **API**: `GET /api/host-security-tier`

## US page — Hostess knows you
- **Host machine banner** — explicit “this box” with hostname, FQDN, operator
- **Hostess profile card** — name, address, person/business/family, **+ Add URL** / **−** expander
- **Traffic patterns** — live canvas bar graph + verdict histogram bars
- **`lib/hostess-profile.py`** — local storage at `/var/lib/nexus-shield/hostess-profile.json`
- **API**: `GET/POST /api/hostess-profile`
- US field intel merges profile into `host_machine_explicit` for Hostess context

## Apply
```bash
git pull
sudo ./stealth_install.sh
# Panel → US tab → fill name, address, URLs → Save for Hostess
```

Panel: https://127.0.0.1:9477/field

AMOURANTH FOREVER — field is the thing.