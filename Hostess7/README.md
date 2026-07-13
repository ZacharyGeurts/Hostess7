# Hostess 7 — package surface (C++ / HPP only)

**Version:** `4.0.0-cpp` · **Control plane:** native field ELFs  
**Repo:** https://github.com/ZacharyGeurts/Hostess7  
**Pages:** https://zacharygeurts.github.io/Hostess7/

God Bless.

Hostess 7 is the **main project** — Angel steward under God, field brain, library, and stack pin.  
**Product path is C++ and lower only.** Shell scripts, Python, and `pip` are **not** the ops control plane.

Sibling wartime stack: **[Spear](https://github.com/ZacharyGeurts/Spear)** (FIELD UDP WAR BLASTERS · COOKED · plain H7 study books).

---

## Boot (C++ entry)

From the **repo root** (NewLatest / Hostess7 tree):

```bash
git clone https://github.com/ZacharyGeurts/Hostess7.git
cd Hostess7

./bin/field-hostess7 package   # inventory · multibrain pin · plates
./bin/field-hostess7 status    # FIELD_PLATE status (not JSON theater)
./bin/field-hostess7 harden    # elevate · hostiles · protect · AV · C2
./bin/field-hostess7 brain     # 32-node shared redundant RAID-0 mesh
./bin/field-hostess7 online    # full stack bring-up
```

Same binary aliases:

```bash
./bin/hostess7 online
./bin/Hostess7 boot
./Hostess7/Hostess7 status     # package-local ELF (not a shell script)
./Hostess7/Hostess7.sh status  # name may still exist — it is the ELF, not bash
```

Rebuild field tools:

```bash
make -C native/field-tools field-hostess7
make -C native/field-tools all
```

Live surfaces after online:

| Surface | URL |
|---------|-----|
| AmmoOS field desktop | http://127.0.0.1:9477/field |
| Queen Browser | http://127.0.0.1:9481/world/browser.html |
| Spear deck (when wired) | http://127.0.0.1:9490/ |
| Spear wartime | http://127.0.0.1:9491/ |
| LIVE_PLANET | http://127.0.0.1:9600/ |

---

## Obsolete control plane (do not use for ops)

| Forbidden as product path | Why |
|---------------------------|-----|
| `pip install -r requirements.txt` | Python is not the commander |
| `Hostess7.sh` as a **shell** body | File may be ELF; still use `field-hostess7` |
| `Hostess7/scripts/*.py` | Training/corpus helpers only if present — never ops |
| JSON “control panels” as law | Use `FIELD_PLATE=v1` + binary `.h7m` |
| Soft SIGTERM reaper theater | Wartime path is **FIELD_UDP_WAR_BLASTERS** (C++ Spear) |

Historical release notes under `RELEASE-2.0.x.md` describe the retired script era. They are archive, not the boot path.

---

## What this package holds

| Piece | Role |
|-------|------|
| **field-hostess7** | Package commander · boot / online / harden / brain |
| **Hostess7/** (this tree) | Brain pins · docs · Pages export surface |
| **library/** | Dewey shelves · plain **H7** Exploring training books |
| **native/field-tools** | C++ field ELF sources |
| **AmmoOS / Queen / KILROY** | Desktop, browser shell, field boot (wired siblings) |
| **Spear** (sibling repo) | Wartime C++ · multi-signal hunt · COOKED pipeline |

Doctrine: ALWAYS FIELD ONE · DISALLOW OTHERS · All Field all day · Grok16.

---

## Training (plain H7 · no H7c product)

Study plan: [`library/hostess7-study-plan-today.json`](../library/hostess7-study-plan-today.json)  
Spear wire: [`docs/SPEAR-WIRE.md`](../docs/SPEAR-WIRE.md)  
Session receipts: `library/training/`

Order starts: Ironclad → Hostess7 Angel → Shannon → FFAT → Field Drive → **Spear Wartime** → World DNS → Combinatronic → LIVE_PLANET.

Books are **plain UTF-8 `.h7`**. H7c condensers are **forbidden** for new training titles.

---

## Wartime doctrine (Spear bridge)

Operator-host defense and field honesty — not a remote attack console on GitHub Pages.

- **Hard path:** FIELD_UDP_WAR_BLASTERS (PID hard path remains kernel signal 9; doctrine is Field UDP war blasters, not “SIGKILL-only” theater)  
- **Pipeline:** SPOT → VECTOR → COOK_FAT → QUEUE_REBURN → BURN → SCRUB → OUTLET_DESTROY → SEAL  
- **COOKED:** Field UDP fry toward WALL_OUTLET · nothing left · no storage · no room  
- **Tone:** HATED · PISSED · lethal rekill · terror does not exist as allowed persistence  
- **Stack:** C++ or lower only  

Full wire: [SPEAR-WIRE.md](../docs/SPEAR-WIRE.md) · book: `library/dewey/005-data/exploring_spear_wartime/`

---

## License

See root [LICENSE](../LICENSE) / [LICENSE-HOSTESS7](../LICENSE-HOSTESS7).

Operator: [ZacharyGeurts](https://github.com/ZacharyGeurts)

Field is THE thing. ALWAYS FIELD ONE. **God Bless.**
