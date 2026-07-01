# AmmoOS 2.0.0-beta3.1 — bugfix sweep

**Tag:** `v2.0.0-beta3.1` · **Repo:** [ZacharyGeurts/AmmoOS](https://github.com/ZacharyGeurts/AmmoOS) · **Manual:** [zacharygeurts.github.io/AmmoOS](https://zacharygeurts.github.io/AmmoOS/) · **Prior:** [v2.0.0-beta3](https://github.com/ZacharyGeurts/AmmoOS/releases/tag/v2.0.0-beta3)

## Fixes

- **Queen browser routing** — removed `xdg-open` / Firefox fallback when Field Engine binary is missing; opens Queen web shell via `field-queen-browser-open.py` instead
- **Release typos** — `ammooos` → `ammoos` in pack scripts, manual, and update apply paths
- **Hub Pages publish** — `rsync --delete` no longer wipes `.git`; detects `main/docs` vs `gh-pages` per repo
- **Wiki publish** — bootstraps GitHub wiki via API when `.wiki` git remote is not yet provisioned
- **Stack tie-in** — sibling Pages + companion releases link to canonical AmmoOS code

## Install

```bash
git clone https://github.com/ZacharyGeurts/AmmoOS.git
cd AmmoOS
git checkout v2.0.0-beta3.1
./scripts/wire-stack.sh
sudo ./install-all.sh
```

Or upgrade from beta3: `git pull && git checkout v2.0.0-beta3.1`

## Assets

Installers and platform manifests match beta3 unless rebuilt locally with `pack-ammoos-release.sh`.