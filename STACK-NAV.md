# AmmoOS Stack — navigation hub

**AmmoOS leads.** KILROY is the PC core (ZNetwork absorbed). AmmoOS desktop runs on AMOURANTHRTX. Queen is a standalone browser.

## Stack (bottom → top)

| Layer | Repo | Role | Loopback |
|-------|------|------|----------|
| Hardware | — | witness, no breaks | — |
| **NEXUS C2** | [AmmoOS](https://github.com/ZacharyGeurts/AmmoOS) | command, gates (inside KILROY runtime) | `:9477` |
| **KILROY** | [KILROY](https://github.com/ZacharyGeurts/KILROY) | PC core — network lane, loopback, defense | `127.0.0.1` |
| **AmmoOS** | [AmmoOS](https://github.com/ZacharyGeurts/AmmoOS) | field OS desktop — **AMOURANTHRTX** backend | `:9477/field` |
| **Queen** | [Queen](https://github.com/ZacharyGeurts/Queen) | standalone secured browser | `:9481` |

**Retired:** ZNetwork as separate layer (absorbed into KILROY). AmmoOS inside Queen (sibling model now).

Doctrine: `data/field-stack-layer-doctrine.json` (v2)

## Load OS

```bash
git clone https://github.com/ZacharyGeurts/AmmoOS.git
cd AmmoOS
./scripts/wire-stack.sh
./scripts/kilroy-load-os.sh
```

| Surface | URL |
|---------|-----|
| AmmoOS desktop | http://127.0.0.1:9477/field |
| Queen Browser (standalone) | http://127.0.0.1:9481/world/browser.html |
| KILROY terminal / API | http://127.0.0.1:9481/api/kilroy |
| Grok Lab | http://127.0.0.1:9477/grok-lab |

## Repo map

| Repo | Pages | What it is |
|------|-------|------------|
| **[AmmoOS](https://zacharygeurts.github.io/AmmoOS/)** | manual | Field OS tree, NEXUS C2, install |
| **[KILROY](https://zacharygeurts.github.io/KILROY/)** | manual | PC core kernel, load-os, real terminal |
| **[Queen](https://zacharygeurts.github.io/Queen/)** | hub | Standalone browser shell |
| **[AMOURANTHRTX](https://github.com/ZacharyGeurts/AMOURANTHRTX)** | — | AmmoOS desktop display technology |
| **[Grok16](https://zacharygeurts.github.io/Grok16/)** | manual | Sovereign `g16` compiler |

## Version line

| Component | Version |
|-----------|---------|
| AmmoOS | `2.0.0-beta3.1` |
| KILROY | `1.1.0 Sanctuary` |
| Grok16 | `5.2.0` |
| Queen | ships in AmmoOS tree + Queen hub |

*ZNetwork repo retained for history — runtime lives in KILROY `lib/kilroy-core.sh`.*