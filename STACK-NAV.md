# Field stack — navigation hub (C++ product path)

**Spear** is the wartime / field-storage stack of record.  
**Hostess 7** is the Angel · package · library.  
**No satellite archives.** Public **KILROY** repo is gone. `KILROY_iPXE` and `ZNetwork` are not product paths.

**Product path: C++ and lower only.** No shell / Python / pip as ops control plane.

## Stack (bottom → top)

| Layer | Repo | Role | Loopback |
|-------|------|------|----------|
| Hardware | — | witness, no breaks | — |
| **Spear** | [Spear](https://github.com/ZacharyGeurts/Spear) | Wartime C++ · COOKED · FFAT · fieldmem · LIVE_PLANET · boot harden | `:9490` / `:9491` / `:9600` |
| **Hostess 7** | [Hostess7](https://github.com/ZacharyGeurts/Hostess7) | Angel · package · library · multibrain · field ELFs | `field-hostess7` |
| **AmmoOS** | [AmmoOS](https://github.com/ZacharyGeurts/AmmoOS) | field OS desktop · AMOURANTHRTX (when used) | `:9477/field` |

**Not live repos:** KILROY (deleted) · KILROY_iPXE · ZNetwork · Queen as separate product URL may 404 — browser shell lives with field stack when present.

Wire detail: [docs/SPEAR-WIRE.md](docs/SPEAR-WIRE.md)

## Load (C++)

```bash
# Wartime / storage of record
git clone https://github.com/ZacharyGeurts/Spear.git
cd Spear && make -C src
# spear-wartime · spear-fleet-link · spear-www · spear-planet

# Angel / library / package
git clone https://github.com/ZacharyGeurts/Hostess7.git
cd Hostess7
./bin/field-hostess7 package
./bin/field-hostess7 online
```

Do **not** run `./scripts/wire-stack.sh` / `pip install` as product path.

| Surface | URL |
|---------|-----|
| Spear deck | http://127.0.0.1:9490/ |
| Spear wartime | http://127.0.0.1:9491/ |
| LIVE_PLANET | http://127.0.0.1:9600/ |
| Hostess7 Pages | https://zacharygeurts.github.io/Hostess7/ |
| AmmoOS desktop (if online) | http://127.0.0.1:9477/field |

## Repo map (live)

| Repo | What it is |
|------|------------|
| **[Spear](https://github.com/ZacharyGeurts/Spear)** | Wartime C++ · FIELD_UDP_WAR_BLASTERS · COOKED · FFAT |
| **[Hostess7](https://zacharygeurts.github.io/Hostess7/)** | Angel · library · plain H7 training · field-hostess7 |
| **[Big_Grin_Terrorist_Hunter](https://zacharygeurts.github.io/Big_Grin_Terrorist_Hunter/)** | Deck / hunt surface |
| **[Grok16](https://zacharygeurts.github.io/Grok16/)** | Sovereign compiler (when used) |
| **[AmmoOS](https://github.com/ZacharyGeurts/AmmoOS)** | Field desktop tree (when used) |

## Version line

| Component | Track |
|-----------|--------|
| Spear | C++ wartime · COOKED · field storage |
| Hostess 7 | `4.0.0-cpp` |
| Grok16 | sovereign compiler |

## Wartime doctrine (one line)

**FIELD_UDP_WAR_BLASTERS** · COOKED to WALL_OUTLET · nothing left · HATED · PISSED · C++ only · plain H7 books · **Spear only — no archives**.

## Live hub

**https://zacharygeurts.github.io/Hostess7/** · Spear on GitHub main.

| Live | URL |
|------|-----|
| Hostess7 | https://zacharygeurts.github.io/Hostess7/ |
| Big Grin | https://zacharygeurts.github.io/Big_Grin_Terrorist_Hunter/ |
| Spear | https://github.com/ZacharyGeurts/Spear |
