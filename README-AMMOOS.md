# AmmoOS

![Release](https://img.shields.io/badge/release-1.9.9h-brightgreen)
![Edition](https://img.shields.io/badge/edition-Grok_Expert_Review-blue)
![G16](https://img.shields.io/badge/Grok16-5.1.0-gold)
![Queen](https://img.shields.io/badge/Queen-browser-purple)
![License](https://img.shields.io/badge/license-GPLv3-green)

**AmmoOS** is the **2.0.0-beta3.1** field operating system on **`127.0.0.1`**. **KILROY** is the PC core (ZNetwork absorbed). AmmoOS desktop runs on **AMOURANTHRTX** display technology. **Queen** is a standalone secured browser on `:9481` — not an AmmoOS container. Stack: Hardware → NEXUS C2 → KILROY → AmmoOS → Queen. Load with `./scripts/kilroy-load-os.sh`.

## Live surfaces (after install)

| Surface | URL | Kind |
|---------|-----|------|
| **Host desktop** | http://127.0.0.1:9477/field | Browser — first page |
| **Field command** | http://127.0.0.1:9477/command | Browser — full C2 |
| **Queen Browser** | http://127.0.0.1:9481/world/browser.html | Browser — standalone shell |
| **Underlay F9** | http://127.0.0.1:9477/underlay-f9?sector=underlay | Browser — Tristate installer |
| **Training** | http://127.0.0.1:9477/command#training | Browser — Hostess7 tab |
| **Queen shell** | `Queen/build/rtx/bin/Linux/queen-browser` | Native — RTX program |
| **Dev launcher** | `./nexus.sh` | Native — panel + browser |

## Quick install (Linux x86_64)

```bash
git clone https://github.com/ZacharyGeurts/AmmoOS.git
cd AmmoOS
sudo ./install-all.sh
```

Browser opens **http://127.0.0.1:9477/field** on start.

## Release pipeline (1.0)

```bash
export SG_ROOT=/path/to/SG
./scripts/ammoos-beta-pipeline.sh    # combinatronic · plate · engine · integrate
./scripts/ammoos-launch-verify.sh     # surfaces · sovereignty · local DNS/DHCP
./scripts/pack-ammoos-release.sh --version 1.0.0
```

## Combinatronic integration

AmmoOS runs the full **g16 combinatronic optimal** cycle before release:

- **Rebalance** — chip + program batteries, universal leaf ordering
- **Condense** — plate width × length consolidation
- **Combine** — universal panel + combinatorics publish
- **Connect** — chip ISA ↔ language driver edges
- **Spider wire** — ironclad outward lane optimization

Doctrine: `lib/g16-combinatronic-rebalance.py` · State: `.nexus-state/ammoos-*.json`

## Platform matrix

AmmoOS 1.0 ships **source bootstrap** for:

| Platform | Installer |
|----------|-----------|
| Linux x86_64 | `install-all.sh` |
| Linux aarch64 / arm / riscv64 / i386 | `install-all.sh` on target |
| Windows x86_64 | `stealth.ps1` or WSL2 + `install-all.sh` |
| macOS (Intel / Apple Silicon) | `./nexus.sh` dev tree |
| FreeBSD amd64 | `install.sh` |
| Android aarch64 | Queen `browser.html` WebView shell |

Full matrix: [ammoos-2.0.0-beta-PLATFORMS.md](dist/ammoos-2.0.0-beta-PLATFORMS.md) · JSON: `data/ammoos-platform-release.json`

## Architecture

```
Host browser (:9477)
  ├─ /field        → host desktop (apps + startbar)
  ├─ /command      → threat panel + training
  └─ /underlay-f9  → Tristate installer

Queen Browser (:9481)
  └─ /world/browser.html → field OS inside Start tab

Native programs
  ├─ queen-browser     → RTX shell (FIELDC / AmmoOS guest)
  ├─ nexus.sh          → dev launcher
  └─ install-all.sh    → production deploy

Combinatronic engine
  ├─ g16-combinatronic-rebalance.py
  ├─ field-program-combinatronic.py
  └─ Queen/AmmoOS/net/*.fld plates
```

## Manual

| Doc | URL |
|-----|-----|
| **Web manual** | https://zacharygeurts.github.io/AmmoOS/ |
| Getting Started | https://zacharygeurts.github.io/AmmoOS/getting-started.html |
| Launch surfaces | https://zacharygeurts.github.io/AmmoOS/launch-surfaces.html |
| Combinatronic | https://zacharygeurts.github.io/AmmoOS/combinatronic.html |
| Platforms | https://zacharygeurts.github.io/AmmoOS/platforms.html |
| Field I/O | https://zacharygeurts.github.io/AmmoOS/io.html |

## Lineage

AmmoOS beta **2.0.0-beta** packages **NEXUS-Shield / NewLatest 10.4.1** with Grok16 **4.7.1** pairing and **KILROY Field Die** syscall truth. Full SG stack siblings are wired and materialized in release archives.

**Release notes:** [RELEASE-2.0.0-beta.md](RELEASE-2.0.0-beta.md)