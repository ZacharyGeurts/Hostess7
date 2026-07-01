# Grok Expert Review

**AmmoOS 1.9.9h**  
**Codename:** View  
**Date:** 2026-06-29  
**Lineage:** SG/NewLatest → github.com/ZacharyGeurts/AmmoOS via MCP layer

## Loopback identity

When **ZNetwork is running**, AmmoOS is **`127.0.0.1`** — the sovereign field OS on loopback, **not** Firefox/Chromium or “just a website.” Queen Browser is the secured system shell; ZNetwork owns 100% of the internet pipe. The startbar clock shows `127.0.0.1` when the pipe is live.

## Stack layering

AmmoOS is embedded **inside Queen**, not a sibling product:

| Layer | Role |
|-------|------|
| **Hardware** | Witness and wire — no breaks, no SPI flash, coexist host desktop |
| **NEXUS C2** | Command, security, defense (`:9477`) |
| **ZNetwork** | 100% internet pipe on loopback |
| **Queen** | Secured browser shell — defends the field |
| **AmmoOS** | Field OS inside Queen — View, Start, native programs |

Doctrine: `data/field-stack-layer-doctrine.json` · API: `/api/field-stack-layer`

## Highlights

- **Queen rebrand** — Firefox/FieldFox UI removed; `queen-browser-guide.html`, crown glyph, field-gecko manifest
- **View** — folder manager reborn from scratch (replaces Nemo / queen-files branding)
- **Program-glyph icons** — OCR-shaped icons per app; portrait/Amouranth tray branding removed
- **Enhanced Start button** — AmmoOS glyph + label, emerald secured chrome
- **Grok16 5.0.1 `ammoos` profile** — `cmake/grok16-profile-ammoos.cmake`, `grok16-integrate.sh` wiring, `grok16-verify-ammoos.sh`, smoke chamber
- **Kill Grok Orphans 1.1.0** — companion watchdog for reparented bash leaks (multi-platform)
- **MCP GitHub layer** — `data/ammoos-mcp-layer.json` + `scripts/github-mcp-stdio.sh` publish path

## Expert reviews

| Reviewer | Verdict | Notes |
|----------|---------|-------|
| **Stack layering** | PASS | Hardware no-break; NEXUS C2 → ZNetwork → Queen → AmmoOS inside Queen |
| **Queen rebrand** | PASS | User guide, crown SVG, sovereignty doctrine v2; legacy gecko binaries only under hood |
| **Field Security** | PASS | Amouranth live tile removed; `no_client_browser` + Queen-only web shell intact |
| **Icon / UX** | PASS | `queen-icon-kit.py` glyph mode; start bar uses `queen-prog-ammoos` not portrait |
| **Folder manager** | PASS | `view.html` canonical; `queen-files` legacy alias; nemo blocked at install |
| **Grok16 incorporation** | PASS | `ammoos` profile, integrate + verify scripts, `AMMOOS-REVIEW-FOR-GROK-BUILD.md` in Grok16 |
| **MCP publish** | PASS | `ammoos-release.sh --push` + GitHub MCP stdio for ZacharyGeurts repos |
| **Launch surfaces** | PASS | `:9477/field`, `:9481/world/view.html`, combinatronic gates in version manifest |
| **Friendly review** | PASS | Post-Grok16 integration — field desktop past prototype; see `docs/AMMOOS-FRIENDLY-REVIEW.md` |

## Combined verify (Grok16 + AmmoOS)

```bash
export SG_ROOT=/path/to/SG
./Grok16/scripts/grok16-verify-ammoos.sh   # ammoos profile smoke + integrate manifest
./NewLatest/scripts/ammoos-launch-verify.sh # sovereignty 100% pipe, DNS/DHCP, stack layers
```

**2026-06-29:** Both gates PASS. Grok16 pairs at **v5.0.1**.

## Friendly review (post-Grok16)

AmmoOS is the runtime half Grok16 was built to feed — dual browser + native surfaces, loopback sovereignty, combinatronic discipline upstream. Still raw on repo hygiene and native VFS stamps; momentum is real. Full text: `docs/AMMOOS-FRIENDLY-REVIEW.md`.

## Install

```bash
git clone https://github.com/ZacharyGeurts/AmmoOS.git
cd AmmoOS
sudo ./install-all.sh
```

## MCP publish (dev)

```bash
export SG_ROOT=/path/to/SG
./scripts/github-mcp-private-setup.sh
./scripts/ammoos-release.sh --version 1.9.9h --push
```

## View

Open **http://127.0.0.1:9481/world/view.html** — sovereign folder manager with program icon library and KILROY terminal roots.