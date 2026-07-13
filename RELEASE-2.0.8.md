# Hostess7 2.0.8 — Field Research v2 · AmmoCodium · sealed generation

**Tag:** `v2.0.8` · **Pairs:** Grok16 5.x · AmmoCode 6.1 · AmmoOS 2.0 · Field Research **2.0** · **AmmoCodium**

## What's new (stack tech)

- **Field Research v2** — research manual reoriented: zero-cost security, field speeds, CHIPs-from-CHIPs; combinatorics tree + plate meld **tombstoned** on the hot path  
  Live: https://zacharygeurts.github.io/Field_Research/  
  Seal: `SHA256:aVYElqiNin1Q/gcaqa6CGGbJ/gjjG9KXP5ZsXg8uMD8`
- **Sealed generation** — posture truth is one generation + profile_id + capability mask (not 30-plate fuse)
- **GuardChip (C3)** design — INPUT/VIEW/CONTEXT zero-cost deny for keylog & capture (extends 4-slot TIME/MEMORY/THERMO/CONTEXT)
- **CHIPs from CHIPs** — C0 Host · C1 Era · C2 Box · C3 Guard · C4 Wire; catalog is literature, not runtime combinatorics
- **AmmoCodium** — sovereign Code-OSS IDE build plane (`ZacharyGeurts/AmmoCodium`); sibling to AmmoCode (light loopback editor)
- **Fixed g16 profiles** — belt_2_0 / field_opt / field_physics chosen explicitly; no tree walk for exec posture
- **Stack map updated** — old-projects + FIELD-STACK doctrine reflect v2 research conclusions

## What stayed (Hostess core)

- Hostess 7 remains **main project** (brain hub, counsel, truth doctrine)
- KILROY = 127.0.0.1 PC core · NEXUS C2 :9477 · Queen :9481
- 4-slot tamper verify · war harden · github-brain mirror
- Packaging / cohesion / war-train from 2.0.7j baseline

## Deprecated (do not build new hot paths)

| Tombstone | Replacement |
|-----------|-------------|
| Combinatorics tree / studio crank | Fixed profiles + sealed generation |
| Plate meld 30-source fuse | One posture artifact + generation |
| Runtime chips-combinatorics | CHIPs C0–C4 composition |

Offline benches and historical panels may remain as archaeology.

## Boot (real brain)

```bash
git clone https://github.com/ZacharyGeurts/Hostess7.git
cd Hostess7
pip install -r requirements.txt
./Hostess7.sh boot
# → http://127.0.0.1:8080/
```

## Stack-learn (absorb new doctrine)

```bash
./Hostess7.sh stack-learn
./Hostess7.sh stack status
```

## Verify

```bash
pip install -e ".[dev]"
python scripts/hostess7-sync-version.py
# expect 2.0.8
hostess7-cohesion
./Hostess7.sh stack "sealed generation"
```

## Sibling repos (latest)

| Repo | Role |
|------|------|
| [Field_Research](https://github.com/ZacharyGeurts/Field_Research) | Research book v2.0 |
| [AmmoCodium](https://github.com/ZacharyGeurts/AmmoCodium) | Full IDE (Code-OSS / Ammo brand) |
| [AmmoCode](https://github.com/ZacharyGeurts/AmmoCode) | Light loopback editor :9555 |
| [Grok16](https://github.com/ZacharyGeurts/Grok16) | g16 field compiler |
| [AmmoOS](https://github.com/ZacharyGeurts/AmmoOS) | Field OS / NEXUS |

## GitHub + Pages

```bash
# From NewLatest/Hostess7 after sync:
./Hostess7.sh h7-optimise --apply
# publish source + pages via your usual publish scripts
```

Live: https://zacharygeurts.github.io/Hostess7/
