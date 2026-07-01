# AmmoOS 2.0.0-beta

**Tag:** `v2.0.0-beta` · **Lineage:** NEXUS-Shield 10.4.1 · **Grok16:** 4.7.1 · **KILROY:** Field Die · **Platforms:** 10

## What shipped

- **KILROY Field Die** — kernel lives beside SG; `lib/kilroy-resolve.sh`, `Queen/lib/queen-kilroy.py`, forged kilroy icons, Tristate virtual field boot
- **Full SG stack wired** — `scripts/wire-stack.sh` symlinks KILROY, Grok16, AMOURANTHRTX, Final_Eye/Ear, ZNEWOCR, ZOCR, ZNetwork, World_Redata, Field_Primer, Spiderweb
- **Underlay F9 Tristate** — bottom-up field installer; KILROY owns syscall truth; non-destructive guest substrate migration
- **Queen KILROY bridge** — field substrate, kernel telemetry, AMOURANTHRTX engine pairing, ecosystem repo status
- **Combinatronic optimal pipeline** — rebalance, condense, combine, connect before pack
- **Launch registry** — every surface as browser URL or native program path
- **Queen AmmoOS plates** — `Queen/AmmoOS/net/*.fld` guest networking fused into engine
- **Hostess7 + training** — codecraft chamber, adaptive IQ, voice, self-interaction training viewer
- **Multi-platform releases** — Linux, Windows, macOS, FreeBSD, Android bootstrap matrix
- **GitHub Pages manual** — full operator manual at zacharygeurts.github.io/AmmoOS

## Install (Linux x86_64)

```bash
tar -xzf ammooos-2.0.0-beta-source.tar.gz
cd ammooos-2.0.0-beta
sudo ./install-all.sh
```

KILROY resolves via `KILROY_ROOT` or sibling `../KILROY`. To lift kernel out of bundle:

```bash
./scripts/kilroy-extract.sh symlink
export KILROY_ROOT=$(./lib/kilroy-resolve.sh)
```

## Surfaces

| URL | Role |
|-----|------|
| http://127.0.0.1:9477/field | Host desktop — first page |
| http://127.0.0.1:9477/command | Field C2 command deck |
| http://127.0.0.1:9481/world/browser.html | Queen Browser OS shell |
| http://127.0.0.1:9477/underlay-f9?sector=underlay | Underlay F9 Tristate |
| http://127.0.0.1:9477/underlay-f9?sector=kilroy | KILROY field underlay |
| http://127.0.0.1:9477/command#training | Hostess7 training viewer |

## Release assets

| Asset | Contents |
|-------|----------|
| `ammoos-2.0.0-beta-source.tar.gz` | Full AmmoOS tree + materialized stack siblings (KILROY, Grok16, …) |
| `ammoos-2.0.0-beta-installers.tar.gz` | install-all, nexus, stealth scripts |
| `ammoos-2.0.0-beta-windows-x86_64.zip` | Windows PowerShell bootstrap |
| `ammoos-2.0.0-beta-platforms.json` | Platform bootstrap matrix |
| `ammoos-2.0.0-beta-PLATFORMS.md` | Human-readable platform guide |

## Beta pipeline

```bash
./scripts/ammoos-beta-pipeline.sh
./scripts/ammoos-launch-verify.sh
./scripts/ammoos-release.sh --version 2.0.0-beta --push
```

## Gates

1. Combinatronic optimal cycle writes `.nexus-state/ammoos-combinatronic-optimal.json`
2. Launch verify passes browser + program registry
3. KILROY resolves via `kilroy-resolve.sh` or materialized `KILROY/` in export
4. Platform manifest lists 10 target families
5. GitHub Pages manual builds from `docs/build-ammoos-manual.py`