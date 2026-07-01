# Release 1.0.0-beta

**Tag:** [`v1.0.0-beta`](https://github.com/ZacharyGeurts/Hostess7/releases/tag/v1.0.0-beta)  
**Repo:** [ZacharyGeurts/Hostess7](https://github.com/ZacharyGeurts/Hostess7)

Complete field stack beta — Hostess 7 brain hub with AmmoOS, Grok16, Queen, KILROY, and stack siblings.

---

## What shipped

- **Hostess 7 brain** — training campus, H7B storage, curiosity corpus, Fifth Amendment literacy, positional awareness
- **AmmoOS field desktop** — panel `:9477`, threat panel, ironclad plate meld
- **Grok16** — compiler toolchain @ 16.2.0
- **Queen** — standalone RTX browser `:9481`
- **Stack wire** — materialized siblings in one tree (`wire-stack.sh`)
- **Historic truth corpus** — gate for all new information
- **Train-before-update** — full curriculum before pack/push

---

## Release assets

| Asset | Contents |
|-------|----------|
| `hostess7-1.0.0-beta-source.h7e` | Full stack tree (extractable) |
| `hostess7-1.0.0-beta-installers.tar.gz` | install-all, wire-stack, unpack scripts |
| `hostess7-1.0.0-beta-platforms.json` | Platform matrix |
| `hostess7-1.0.0-beta-PLATFORMS.md` | Platform guide |

---

## Install

```bash
./scripts/field-h7e-extract.sh hostess7-1.0.0-beta-source.h7e
cd hostess7-1.0.0-beta
./scripts/wire-stack.sh
sudo ./install-all.sh
./Hostess7/Hostess7.sh on
```

---

## Release pipeline (operator)

```bash
./lib/ammolang-run.sh hostess7_train_before_update
./lib/ammolang-run.sh hostess7_release
```

Monitor:

```bash
tail -f .nexus-state/hostess7-release-progress.json
```

Publish wiki:

```bash
bash scripts/publish-hostess7-wiki.sh
```