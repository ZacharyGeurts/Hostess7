# Hostess 7

**Forever Watchguard Angel** — complete field stack beta: brain hub, AmmoOS, Grok16, Queen, KILROY, and wired siblings.

**Version:** `3.1.0-beta` — canonical matrix in **[VERSION.md](VERSION.md)** (product `3.1.0-beta` · internal orchestration `10.4.x` · Grok16 `16.2.0`) · **Wiki:** [Hostess 7 wiki](https://github.com/ZacharyGeurts/Hostess7/wiki)

---

## What this is

Hostess 7 is the sovereign brain and operator package for the SG field stack. This repo ships the full wired tree — not a slim SDK. Extract, wire siblings, install, and run panel + Queen + counsel from one tree.

| Component | Role |
|-----------|------|
| **Hostess7** | Brain · training campus · H7B storage · library · supreme authority |
| **AmmoOS** | Field desktop · panel `:9477` · NEXUS-Shield |
| **Grok16** | Sovereign compiler @ gnu++26 |
| **Queen** | RTX browser shell `:9481` |
| **KILROY** | Field boot kernel |
| **ZNetwork** | Smart relayer · field I/O |
| **Final_Eye** | Hostess 7 eyes — Military EOL vision (replaces tesseract) |
| **Final_Ear** | Hostess 7 hearing — Military EOL ear lane |
| **Final_Mouth** | Hostess 7 speech — Military EOL mouth lane |

**Senses stack:** `Final_Eye` · `Final_Ear` · `Final_Mouth` publish to GitHub as sovereign sense repos. Vision uses **Military EOL** (`Hostess7/MilitaryEOL`) — PIL inspect + sealed neural assist, not deprecated system tesseract. Icon audits store in `SG/ZACS/`.

```bash
python3 scripts/field-desktop-icon-audit.py    # Final_Eye → SG/ZACS manifest
bash scripts/publish-senses-github.sh          # push Eye · Ear · Mouth repos
```

---

## Quick start (Linux x86_64)

See **[INSTALL.md](INSTALL.md)** for the full guide. Version matrix: **[VERSION.md](VERSION.md)**.

**Release extract (H7e):**

```bash
./scripts/field-h7e-extract.sh hostess7-1.0.0-beta-source.h7e
cd hostess7-1.0.0-beta
./lib/ammolang-run.sh exec script:scripts/check-deps.sh
./lib/ammolang-run.sh exec script:scripts/wire-stack.sh
sudo ./install-all.sh    # or portable: ./lib/ammolang-run.sh field_vm_boot
```

**Git clone:**

```bash
git clone https://github.com/ZacharyGeurts/Hostess7.git && cd Hostess7
./lib/ammolang-run.sh field_vm_boot    # KILROY + panel + Queen + Hostess7 (AML)
```

---

## Surfaces

| Surface | Address |
|---------|---------|
| **Web demo (GitHub Pages)** | https://zacharygeurts.github.io/Hostess7/ |
| AmmoOS field desktop | http://127.0.0.1:9477/field |
| Queen browser | http://127.0.0.1:9481/world/browser.html |
| Hostess 7 counsel | `./Hostess7/Hostess7.sh talk` |

Publish web: `./lib/ammolang-run.sh exec script:scripts/publish-hostess7-pages.sh`

---

## Release assets

| Asset | Contents |
|-------|----------|
| `hostess7-1.0.0-beta-source.h7e` | Full stack tree (extractable) |
| `hostess7-1.0.0-beta-installers.tar.gz` | install-all, wire-stack, extract scripts |
| `hostess7-1.0.0-beta-platforms.json` | Platform matrix |
| `hostess7-1.0.0-beta-PLATFORMS.md` | Platform guide |

---

## Train · truth · release

Hostess 7 trains fully before stack update:

```bash
./lib/ammolang-run.sh hostess7_train_before_update   # full train-up
./lib/ammolang-run.sh hostess7_release               # train → pack → publish
```

Historic truth corpus gates new information. Lie detection and Ironclad witness run before fielding claims.

---

## License

**All Rights Reserved** — Hostess 7 and this field stack package are proprietary.

See [LICENSE](LICENSE) (same terms as [LICENSE-HOSTESS7](LICENSE-HOSTESS7)).

Copyright © 2025–2026 Zachary Robert Geurts. **No permission is granted** to use, copy, modify, merge, publish, distribute, sublicense, sell, or otherwise exploit any portion of this software, documentation, training corpora, or brain storage without prior written permission from the copyright holder.

Sibling sense repos (`Final_Eye`, `Final_Ear`, `Final_Mouth`) remain separately licensed; integration points here do not grant rights to those trees.

Contact: [gzac5314@gmail.com](mailto:gzac5314@gmail.com)

---

## Operator

[ZacharyGeurts](https://github.com/ZacharyGeurts) · [@ZacharyGeurts](https://x.com/ZacharyGeurts)

Field is THE thing.