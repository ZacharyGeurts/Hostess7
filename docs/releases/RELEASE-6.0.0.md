# NEXUS-Shield 6.0.0

Major release — Hostess7 runs the show, live panel only, Hell Kit, precision field.

## Highlights

- **v6.0.0** — version line across panel, daemon, and GitHub releases
- **No client cache** — panel fetches `/api/status` live; removed field-snapshot and sessionStorage stubs
- **Hostess7 unified** — TEAM NVMe fieldstorage primary, desktop cache fallback; autonomous sync + GitHub update planning
- **Hell Kit** — sever wire, regional disable, human threat sweep, Heaven/Hell rip
- **Precision map & spiderweb** — sub-micron GPS placement
- **Panel UX** — dark dropdowns with white text; tab load badges hidden; all tabs paint real data (no perpetual Loading…)

## Install

```bash
cd /home/default/Desktop/SG/Latest/NEXUS-Shield
sudo ./stealth_install.sh
```

## Hostess7 operator

```bash
cd /home/default/Desktop/SG/Hostess7
./Hostess7.sh on
./Hostess7.sh team-sync
./Hostess7.sh nexus status
./Hostess7.sh nexus update          # plan
HOSTESS7_EXEC=1 ./Hostess7.sh nexus update --apply
```

## Panel

https://127.0.0.1:9477/field

God Bless.