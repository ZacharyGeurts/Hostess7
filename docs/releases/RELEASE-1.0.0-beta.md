# AmmoOS 1.0.1-beta

**Tag:** `v1.0.1-beta` · **Lineage:** NEXUS-Shield 10.4.1 · **Grok16:** 4.7.1 · **Platforms:** 10

## What shipped

- **AmmoOS product repo** — SG/NewLatest field stack as standalone field OS beta
- **Combinatronic optimal pipeline** — rebalance, condense, combine, connect before pack
- **Launch registry** — every surface as browser URL or native program path
- **Queen AmmoOS plates** — `Queen/AmmoOS/net/*.fld` guest networking fused into engine
- **Multi-platform releases** — Linux, Windows, macOS, FreeBSD, Android bootstrap matrix
- **GitHub Pages manual** — full operator manual at zacharygeurts.github.io/AmmoOS

## Install (Linux x86_64)

```bash
tar -xzf ammooos-1.0.1-beta-source.tar.gz
cd ammooos-1.0.1-beta
sudo ./install-all.sh
```

## Surfaces

| URL | Role |
|-----|------|
| http://127.0.0.1:9477/field | Host desktop — first page |
| http://127.0.0.1:9477/command | Field C2 command deck |
| http://127.0.0.1:9481/world/browser.html | Queen Browser OS shell |
| http://127.0.0.1:9477/underlay-f9?sector=underlay | Underlay F9 Tristate |

## Release assets

| Asset | Contents |
|-------|----------|
| `ammoos-1.0.1-beta-source.tar.gz` | Full AmmoOS tree |
| `ammoos-1.0.1-beta-installers.tar.gz` | install-all, nexus, stealth scripts |
| `ammoos-1.0.1-beta-windows-x86_64.zip` | Windows PowerShell bootstrap |
| `ammoos-1.0.1-beta-platforms.json` | Platform bootstrap matrix |
| `ammoos-1.0.1-beta-PLATFORMS.md` | Human-readable platform guide |

## Beta pipeline

```bash
./scripts/ammoos-beta-pipeline.sh
./scripts/ammoos-launch-verify.sh
```

## Gates

1. Combinatronic optimal cycle writes `.nexus-state/ammoos-combinatronic-optimal.json`
2. Launch verify passes browser + program registry
3. Platform manifest lists 10 target families
4. GitHub Pages manual builds from `docs/build-ammoos-manual.py`