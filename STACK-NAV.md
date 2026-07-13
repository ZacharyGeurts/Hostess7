# Field stack — navigation hub (C++ product path)

**Hostess 7** is the main package. **AmmoOS** is field desktop. **KILROY** is PC core / boot.
**Spear** is wartime C++. **Queen Browser** is the field web engine (`:9481`).
**Queen Room** is movies + emulator launch.

**Product path: C++ and lower only.** No shell / Python / pip as ops control plane.

## Stack (bottom → top)

| Layer | Repo | Role | Loopback |
|-------|------|------|----------|
| Hardware | — | witness, no breaks | — |
| **KILROY** | [KILROY](https://github.com/ZacharyGeurts/KILROY) | PC core · network lane · defense | `127.0.0.1` |
| **Hostess 7** | [Hostess7](https://github.com/ZacharyGeurts/Hostess7) | Angel · package · library · multibrain | field ELFs |
| **Spear** | [Spear](https://github.com/ZacharyGeurts/Spear) | Wartime C++ · COOKED · FFAT · LIVE_PLANET | `:9490` / `:9491` / `:9600` |
| **AmmoOS** | [AmmoOS](https://github.com/ZacharyGeurts/AmmoOS) | field OS desktop · AMOURANTHRTX | `:9477/field` |
| **Queen Browser** | [Queen](https://github.com/ZacharyGeurts/Queen) | Field Gecko secured browser shell | `:9481` |

**Retired as separate product:** ZNetwork (absorbed into KILROY). Script-era `Hostess7.sh` bash boot (ELF name may remain — use `field-hostess7`).

Wire detail: [docs/SPEAR-WIRE.md](docs/SPEAR-WIRE.md)

## Load OS (C++)

```bash
git clone https://github.com/ZacharyGeurts/Hostess7.git
cd Hostess7
./bin/field-hostess7 package
./bin/field-hostess7 online
# Spear sibling (when installed):
# spear-wartime · spear-fleet-link · spear-www · spear-planet
```

Do **not** run `./scripts/wire-stack.sh` / `pip install` as product path.

| Surface | URL |
|---------|-----|
| AmmoOS desktop | http://127.0.0.1:9477/field |
| Queen Browser | http://127.0.0.1:9481/world/browser.html |
| Queen Room | http://127.0.0.1:9481/world/queen-game-room.html |
| Spear deck | http://127.0.0.1:9490/ |
| Spear wartime | http://127.0.0.1:9491/ |
| LIVE_PLANET | http://127.0.0.1:9600/ |
| Hostess7 Pages | https://zacharygeurts.github.io/Hostess7/ |

## Repo map

| Repo | Pages / hub | What it is |
|------|-------------|------------|
| **[Hostess7](https://zacharygeurts.github.io/Hostess7/)** | Pages | Main package · library · Angel |
| **[Spear](https://github.com/ZacharyGeurts/Spear)** | GH | Wartime C++ · FIELD_UDP_WAR_BLASTERS · COOKED |
| **[KILROY](https://zacharygeurts.github.io/KILROY/)** | Pages | PC core · field boot |
| **[AmmoOS](https://zacharygeurts.github.io/AmmoOS/)** | manual | Field OS · NEXUS C2 |
| **[Queen](https://zacharygeurts.github.io/Queen/)** | hub | Browser shell + Queen Room |
| **[Grok16](https://zacharygeurts.github.io/Grok16/)** | manual | Sovereign `g16` compiler |
| **[Big_Grin_Terrorist_Hunter](https://zacharygeurts.github.io/Big_Grin_Terrorist_Hunter/)** | Pages | Deck / hunt surface |

## Version line

| Component | Version / track |
|-----------|-----------------|
| Hostess 7 | `4.0.0-cpp` |
| Spear | C++ wartime (FIELD_UDP / COOKED) |
| KILROY | field boot / iPXE plane |
| Grok16 | sovereign compiler |
| Queen Browser | ships with field stack |

## Wartime doctrine (one line)

**FIELD_UDP_WAR_BLASTERS** · COOKED to WALL_OUTLET · nothing left · HATED · PISSED · C++ only · plain H7 books.

## Live hub

**https://zacharygeurts.github.io/Hostess7/** · stack cards also on AmmoOS when that tree is online.

| Live | URL |
|------|-----|
| Hostess7 | https://zacharygeurts.github.io/Hostess7/ |
| KILROY | https://zacharygeurts.github.io/KILROY/ |
| Big Grin | https://zacharygeurts.github.io/Big_Grin_Terrorist_Hunter/ |
