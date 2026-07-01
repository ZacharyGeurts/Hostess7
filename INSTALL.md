# Hostess 7 — Install guide

**Product version:** `1.0.0-beta` · See [VERSION.md](VERSION.md) for the full version matrix.

Two supported paths: **release extract** (H7e) and **git clone** (developer / VM bootstrap).

---

## Prerequisites

Run the dependency check first (always through AML):

```bash
./lib/ammolang-run.sh exec script:scripts/check-deps.sh
```

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| OS | Linux x86_64 | Primary platform; ARM/RISC-V via source bootstrap |
| bash | 5.x | Required for AML boundary scripts |
| python3 | 3.10+ | Panel, Hostess7 brain, training viewer |
| curl | any | Health checks, release fetch |
| git | 2.x | Clone path only |
| rsync | any | Wire-stack, publish |
| optional sudo | — | System install to `/usr/local/lib/nexus-shield` |
| optional cmake/gcc | — | Queen RTX build, Grok16, KILROY kernel |

---

## Path A — Release extract (H7e)

```bash
./scripts/field-h7e-extract.sh hostess7-1.0.0-beta-source.h7e
cd hostess7-1.0.0-beta
./lib/ammolang-run.sh exec script:scripts/check-deps.sh
./lib/ammolang-run.sh exec script:scripts/wire-stack.sh
sudo ./install-all.sh          # system install
# OR portable dev (no sudo):
./lib/ammolang-run.sh field_vm_boot
```

---

## Path B — Git clone (from source)

```bash
git clone https://github.com/ZacharyGeurts/Hostess7.git
cd Hostess7
export NEXUS_INSTALL_ROOT="$PWD"
export SG_ROOT="$(cd .. && pwd)"   # parent of Hostess7 tree if siblings live there
export NEXUS_STATE_DIR="$PWD/.nexus-state"
./lib/ammolang-run.sh field_vm_boot   # deps · wire · KILROY · Hostess7 · training viewer
```

If siblings (KILROY, Grok16, AMOURANTHRTX) live beside the tree:

```
SG/
  Hostess7/          ← git clone (or NewLatest checkout)
  KILROY/
  Grok16/
  Queen/
  ...
```

`wire-stack.sh` links them into the operational tree automatically.

---

## Surfaces after boot

| Surface | URL |
|---------|-----|
| AmmoOS field desktop | http://127.0.0.1:9477/field |
| Command deck | http://127.0.0.1:9477/command |
| Queen browser | http://127.0.0.1:9481/world/browser.html |
| Training viewer | http://127.0.0.1:9488/ |
| Hostess7 counsel | `./Hostess7/Hostess7.sh talk` |

---

## VM / KILROY bootstrap

On a clean Linux VM (Mint, Ubuntu, etc.):

```bash
./lib/ammolang-run.sh field_vm_boot    # wire + KILROY + stack + Hostess7 (AML boundary)
```

KILROY Tristate virtual field (external drive, host stays safe):

```bash
./scripts/tristate-virtual-kilroy-field.sh
```

---

## System install vs portable

| Mode | Entry | State dir |
|------|-------|-----------|
| **System** | `sudo ./install-all.sh` | `/var/lib/nexus-shield` |
| **Portable** | `./lib/ammolang-run.sh field_vm_boot` | `.nexus-state` or `.nexus-field-drive/nexus-field/state` |

---

## Train before release

```bash
./lib/ammolang-run.sh hostess7_train_before_update
./lib/ammolang-run.sh hostess7_release
```

---

## Related docs

- [README-HOSTESS7.md](README-HOSTESS7.md) — product overview
- [INSTALL-README.md](INSTALL-README.md) — NEXUS-Shield system installer (`10.4.1`)
- [SECURITY.md](SECURITY.md) — posture and manifest verification
- [scripts/README.md](scripts/README.md) — script layout (`scripts/` vs `scripts/impl/`)