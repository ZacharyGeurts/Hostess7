# AmmoOS 2.0.0-beta5 — CONDENSER

**Tag:** `v2.0.0-beta5` · **Repo:** [ZacharyGeurts/AmmoOS](https://github.com/ZacharyGeurts/AmmoOS) · **Manual:** [zacharygeurts.github.io/AmmoOS](https://zacharygeurts.github.io/AmmoOS/) · **Prior:** [v2.0.0-beta4](https://github.com/ZacharyGeurts/AmmoOS/releases/tag/v2.0.0-beta4)

## Beta 5 highlights

- **H7e source release** — extractable `.h7e` folder archive (double-click / `field-h7e-extract.sh`)
- **H7s CHIPS lane** — structural slice redense for chips batteries (execute without full JSON parse)
- **Monster stall fix** — process-tree vitals; no surprise zenity; C2 task manager hang bar
- **GitHub pack** — drops combinatoric-visuals PNGs, pages-hub clones, Grok16 vendor sources, panel profiles
- **Grok16 chips only** — compiler toolchain + CHIPS JSON; book-cover assets regenerate on demand

## Install

```bash
git clone https://github.com/ZacharyGeurts/AmmoOS.git
cd AmmoOS
git checkout v2.0.0-beta5
./scripts/wire-stack.sh
sudo ./install-all.sh
```

Or from release asset:

```bash
curl -LO …/ammoos-2.0.0-beta5-source.h7e
bash scripts/field-h7e-extract.sh ammooos-2.0.0-beta5-source.h7e
cd ammooos-2.0.0-beta5
sudo ./install-all.sh
```

## Ship lane

```bash
./scripts/ammoos-release.sh --version 2.0.0-beta5 --push
```

## Pairings

| Component | Version |
|-----------|---------|
| Grok16 | 5.2.0 |
| KILROY | 1.1.0 |
| Hostess 7 | supreme authority + component seal |