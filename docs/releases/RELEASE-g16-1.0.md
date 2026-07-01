# NEXUS-Shield g16 1.0

**g16 1.0** — Host desktop first page, Queen Browser OS inside, host freeze, underlay drop/rise.

## Highlights

- **Host desktop** (`/field`) — scans incumbent OS `.desktop` apps, mirrors theme/icons, field startbar overlay (taskbar, clock, long-press, right-click).
- **Field command** (`/command`) — full threat panel C2 unchanged from prior releases.
- **Queen Browser** (`:9481/world/browser.html`) — browser chrome with field OS inside Start tab; Drop ⬇ / Rise ⬆ underlay controls.
- **Host freeze** — soft cgroup, mem sleep (S3), disk hibernate; sovereign gap witness on resume; field draw isolated on soft freeze.
- **Underlay surface API** — `/api/field-underlay-surface` for drop beneath host / rise field slice.
- **Tristate installer** — 7-step flow, root-first, unfield files on drive (Underlay F9).

## Install

```bash
git clone https://github.com/ZacharyGeurts/NEXUS-Shield.git
cd NEXUS-Shield
sudo ./install-all.sh
```

## URLs

| Surface | URL |
|---------|-----|
| Host desktop | http://127.0.0.1:9477/field |
| Field command | http://127.0.0.1:9477/command |
| Queen Browser | http://127.0.0.1:9481/world/browser.html |
| Underlay F9 | http://127.0.0.1:9477/underlay-f9?sector=underlay |

## Docs

- Wiki: https://github.com/ZacharyGeurts/NEXUS-Shield/wiki
- Manual: https://zacharygeurts.github.io/NEXUS-Shield/