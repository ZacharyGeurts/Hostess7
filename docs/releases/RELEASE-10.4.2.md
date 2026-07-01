# NEXUS-Shield 10.4.2

Patch release — boot hardening, painless field conversion, wiki + GitHub Pages manual refresh.

## Highlights

- **Boot path hardening** — install-root validation, trusted-script gate, timeouts, log rotation, explicit integrity logging
- **Field switch safety** — painless Tristate conversion; wave shed on advisory heat; quota holds at field-max unless thermal crit
- **No surprise slowdowns** — `NEXUS_FIELD_NO_UNEXPECTED_SLOWDOWN=1`; conversion blocks only at crit
- **Release tooling** — `nexus-release-finalize.sh`, CLI flags on pack/release/bump, `SECURITY.md`
- **Wiki + Pages** — updated for v10.4.2; new field-switch-safety diagram; illustrated manual at GitHub Pages

## Install

```bash
tar -xzf nexus-shield-10.4.2-source.tar.gz
cd nexus-shield-10.4.2
sudo ./install-all.sh
```

## URLs

| Surface | URL |
|---------|-----|
| Field panel | http://127.0.0.1:9477/field |
| Underlay F9 | http://127.0.0.1:9477/underlay-f9?sector=underlay |
| Manual (Pages) | https://zacharygeurts.github.io/NEXUS-Shield/ |
| Wiki | https://github.com/ZacharyGeurts/NEXUS-Shield/wiki |

## Release assets

- `nexus-shield-10.4.2-source.tar.gz` — full tree
- `nexus-shield-10.4.2-installers.tar.gz` — installer scripts only