# AmmoOS 1.9.9 Pre Grok Heavy

**Codename:** View  
**Date:** 2026-06-29  
**Lineage:** SG/NewLatest → github.com/ZacharyGeurts/AmmoOS via MCP layer

## Loopback identity

When **ZNetwork is running**, AmmoOS is **`127.0.0.1`** — the sovereign field OS on loopback, **not** Firefox/Chromium or “just a website.” Queen Browser is the system shell; ZNetwork owns 100% of the internet pipe. The startbar clock shows `127.0.0.1` when the pipe is live.

## Highlights

- **View** — folder manager reborn from scratch (replaces Nemo / queen-files branding)
- **Program-glyph icons** — OCR-shaped icons per app; portrait/Amouranth tray branding removed
- **Enhanced Start button** — AmmoOS glyph + label, emerald secured chrome
- **MCP GitHub layer** — `data/ammoos-mcp-layer.json` + `scripts/github-mcp-stdio.sh` publish path
- **Grok16 5.0.0** — compile-ready, secured native path (`GROK16_ROOT`, `g16 -std=gnu17`)
- **Kill Grok Orphans** — companion watchdog for reparented bash leaks

## Expert reviews

| Reviewer | Verdict | Notes |
|----------|---------|-------|
| **Field Security** | PASS | Amouranth live tile removed; `no_client_browser` + Queen-only web shell intact |
| **Icon / UX** | PASS | `queen-icon-kit.py` glyph mode; start bar uses `queen-prog-ammoos` not portrait |
| **Folder manager** | PASS | `view.html` canonical; `queen-files` legacy alias; nemo blocked at install |
| **Grok16 compile** | PASS | Grok16 5.0.0 pairing; static/native builds documented in README-AMMOOS |
| **MCP publish** | PASS | `ammoos-release.sh --push` + GitHub MCP stdio for ZacharyGeurts repos |
| **Launch surfaces** | PASS | `:9477/field`, `:9481/world/view.html`, combinatronic gates in version manifest |

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
./scripts/ammoos-release.sh --version 1.9.9-pre-grok-heavy --push
```

## View

Open **http://127.0.0.1:9481/world/view.html** — sovereign folder manager with program icon library and KILROY terminal roots.