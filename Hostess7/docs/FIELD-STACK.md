# SG Field Stack — How Everything Works

Hostess 7 teaches this stack to every operator. Machine-readable doctrine: `data/field-stack-doctrine.json`.

**Hostess 7 2.0.8** absorbs **Field Research v2** conclusions: zero-cost security, sealed generation, CHIPs-from-CHIPs, fixed g16 profiles. Combinatorics trees and plate-meld fuses are **not** the hot-path nervous system.

## Principle: KILROY is the PC core

**KILROY is `127.0.0.1`** on any computer — transparent, guest OS untouched. It delivers **security** (C2 panel, truth DNS, field protections), **Field Tech speed** (loopback-first services), and **storage space** (field-drive mirror) without bothering the incumbent desktop. **NEXUS C2** (black / green / pink `:9477`) lives inside KILROY. **F9 overrides everyone** — we got the hook.

## Field Research v2 · posture (2026-07)

| Idea | Role |
|------|------|
| **Sealed generation** | One generation + `profile_id` + capability mask — not 30-plate meld |
| **GuardChip** | INPUT / VIEW / CONTEXT (extends 4-slot TIME·MEMORY·THERMO·CONTEXT) — zero tax when calm |
| **CHIPs C0–C4** | Host · Era · Box · Guard · Wire — compose chips from chips |
| **Fixed profiles** | `belt_2_0` / `field_opt` / `field_physics` — no tree walk |
| **AmmoCodium** | Full IDE binary (Code-OSS Ammo brand) — sibling to AmmoCode :9555 |
| **Tombstones** | Combinatorics studio + plate meld offline only |

Research book: https://zacharygeurts.github.io/Field_Research/  
Doctrine seal: `SHA256:aVYElqiNin1Q/gcaqa6CGGbJ/gjjG9KXP5ZsXg8uMD8`

## KILROY self-defensive (always on)

KILROY defends **itself** at the Field Die — not via a userspace daemon the guest can kill:

| Mechanism | Role |
|-----------|------|
| 4-slot tamper verify | TIME / MEMORY / THERMO / CONTEXT integrity |
| NEXUS guard | Amortized behavioral check at syscall boundary |
| `rtx_slots_tamper_action` | Abort task on slot corruption |
| Syscall whitelist | Consumer-safe passthrough only |
| `/proc/kilroy_field/security` | Live telemetry |

This runs **continuously** without operator updates. Guest OS cannot disable it.

## Periodic update process (separate lane)

Self-defense ≠ no updates. The stack still needs **occasional** refresh:

| Lane | When | How |
|------|------|-----|
| **KILROY kernel** | Field Die / physics / security slot changes | `build-kilroy.sh` → `grok-mkimage.sh`; `field-recompile.sh` after `.fld` changes |
| **NEXUS userspace** | Panel, genius, protections | `/ammoos-update-os` · `nexus-update-apply.sh` · `field-mint-boot-ready.sh` |
| **AmmoOS stack** | GitHub release | `ammoos-update-inplace.py` — preflight · lock · apply |
| **Hostess7 brain** | Doctrine changes | `./Hostess7.sh stack-learn` · `./Hostess7.sh updates` |

Rule: updates ship improved images and rules — they **do not** turn off tamper verify during apply.

| Layer | Role |
|-------|------|
| **KILROY PC core** | Syscall truth, **NEXUS C2 panel** (`:9477` black/green/pink), network lane, defense + offense |
| **Unified device field** | One envelope: drives, RAM, motherboard, voltage, FCC |
| **Underlay** | Grandma-safe passthrough — F9 sovereign hook overrides host shortcuts |
| **Guest OS** | Incumbent Linux/Windows — loads normal desktop inside field grant |

## Boot order

**Cold boot (systemd):**

```
kilroy_kernel → unified_device_field → underlay → guest_os
```

(NEXUS C2 panel is inside `kilroy_kernel`.)

- `nexus-field-early.service` — before display-manager (KILROY PC core boards C2 + network)
- `nexus-genius.service` — `lib/nexus-daemon.sh` (must be executable)

**After login — F9:**

```
F9 sovereign hook → kilroy → ammoos
```

F9 engages `field-keyboard-sovereign.py` — host WM shortcuts yield. **Queen = web browser.** **AmmoOS = normal desktop** on F9.

Boot services (DNS/DHCP tables) pre-configured on KILROY boot: `data/kilroy-boot-services.json` · `lib/kilroy-boot-services.py board`.

## Field drive

| Path | Purpose |
|------|---------|
| `NewLatest/.nexus-field-drive` | Live host mirror (publish here) |
| `.../nexus-field/state` | Runtime state, early boot markers |
| Physical TEAM drive | Operator data only — **no nested nexus-field** |

Publish: `pythong lib/field-drive-system.py publish`  
Setup: `bash scripts/field-mint-boot-ready.sh` (sudo when prompted)

## Kill tech map

**Defensive:** seal-vault, tamper-guard, network-lockdown, firewall-sentinel, field-rf-sentinel

**Offensive:** field-attack-kit (autokill/RE-KILL/NO-KILL), pest-arsenal, lethal-enforcement, planetary-observer, relayer retaliation

All anchored in KILROY PC core (`lib/kilroy-core.sh`) — guest malware cannot disable them.

## Health checks

```bash
systemctl is-active nexus-field-early.service nexus-genius.service
curl -sf http://127.0.0.1:9477/field
curl -sf http://127.0.0.1:9481/api/status
pythong lib/field-unified-device.py json
```

**Hostess 7:**

```bash
./Hostess7.sh stack-learn          # install corpus into brain
./Hostess7.sh stack status         # live posture
./Hostess7.sh stack "boot order"   # query doctrine
./Hostess7.sh nexus status         # genius + panel + queen
./Hostess7.sh sg-hub               # SG folder map
```

## Grandma-safe rules

- GRUB / Mint / Windows **unchanged** until Tristate commit
- Underlay **passthrough** — not committed by default
- No hardcoded passwords in repo
- F9 hotkey — no fullscreen hijack; drop-panel wall removed

## Related NewLatest paths

| Area | Path |
|------|------|
| Early boot | `lib/nexus-field-early-boot.sh`, `scripts/nexus-field-early-boot.sh` |
| Unified field | `lib/field-unified-device.py`, `data/field-unified-device-doctrine.json` |
| F9 | `lib/field-queen-browser-open.py`, `lib/field-underlay-hotkey.py` |
| Mint setup | `scripts/field-mint-boot-ready.sh` |
| KILROY PC core | `lib/kilroy-core.sh`, `NewLatest/KILROY/` (userspace graft until bzImage live) |

## KILROY unified product · Internet 2.0 (2026-07)

**KILROY** is one product (kernel + iPXE face + NEXUS C2 userspace).  
**Internet 2.0** attaches on boot (`i2=1`) *before* guest grant.  
**Secure Layer** is I2 enforcement on the die — not a separate product.

```bash
python3 lib/kilroy-i2-attach.py attach
python3 lib/nexus-c2-harden.py status
```

Docs: `docs/KILROY-UNIFIED-PRODUCT.md` · `boot/kilroy.ipxe`  
Doctrines: `data/kilroy-unified-product-doctrine.json`, `internet-2.0-doctrine.json`, `secure-layer-doctrine.json`, `nexus-c2-harden-doctrine.json`


## Always War · AI defends

Default C2 profile is **war**. AI defense (AI_DEFEND / LETHAL) is first-class under Secure Layer. Boot never starts disarmed.

```bash
export NEXUS_C2_PROFILE=war
python3 lib/nexus-c2-harden.py seal war
```
