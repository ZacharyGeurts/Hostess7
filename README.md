# Hostess 7

God Bless.

**The last computer for the world** — sovereign field stack: full server plane, distributed multibrain, AmmoOS, Grok16, KILROY, Queen, wired siblings.

**Version:** `4.0.0-cpp` · **Control plane:** C++ / HPP only · **No shell · No Python · No JSON control**

| Surface | URL |
|---------|-----|
| **Hostess7 Pages (start here)** | https://zacharygeurts.github.io/Hostess7/ |
| **GitHub** | https://github.com/ZacharyGeurts/Hostess7 |
| **AmmoOS field desktop** | http://127.0.0.1:9477/field |
| **Queen Browser** | http://127.0.0.1:9481/world/browser.html |

---

## Quick start (C++ entry)

```bash
git clone https://github.com/ZacharyGeurts/Hostess7.git
cd Hostess7   # or NewLatest tree

./bin/field-hostess7 package   # inventory · multibrain pin · plates
./bin/field-hostess7 status    # FIELD_PLATE status (not JSON)
./bin/field-hostess7 harden    # elevate · hostiles · protect · AV · C2
./bin/field-hostess7 brain     # 32-node shared redundant RAID-0 mesh
./bin/field-hostess7 online    # full stack bring-up
```

Same binary as:

```bash
./bin/hostess7 online
./bin/Hostess7 boot
./Hostess7/Hostess7 status     # package-local ELF (not a shell script)
```

Rebuild field tools:

```bash
make -C native/field-tools field-hostess7
make -C native/field-tools all
```

Open **https://zacharygeurts.github.io/Hostess7/** for Pages, or **http://127.0.0.1:9477/field** after local online for live AmmoOS.

---

## What this is

NewLatest **is** the Hostess 7 package. Ops run on native field ELFs. Plates + `.h7m` replace JSON control panels. Shell and Python are not the control plane.

| Component | Role |
|-----------|------|
| **field-hostess7** | Package commander · boot / online / harden / brain |
| **field-\*** ELFs | DNS · DHCP · mesh · elevate · AV · C2 · plane · H7R |
| **Hostess7/** | Brain pins · docs · Pages surface |
| **AmmoOS** | Field desktop · `:9477` |
| **Grok16** | Sovereign compiler |
| **KILROY** | Field boot / iPXE |
| **Queen** | Browser shell `:9481` |

### Distributed brain

- **32** logical brains · **RAID-0** stripe width **8** · **4** AmmoNet horses  
- Shared · redundant · across our servers (same stack doctrine)  
- Wire: `hostess7-multibrain-field.plate` + `hostess7-multibrain.h7m`  
- ALWAYS FIELD ONE · DISALLOW OTHERS · All Field all day · Grok16  

Doctrine plate: [docs/hostess7-distributed-package.plate](docs/hostess7-distributed-package.plate)  
Full package notes: [README-HOSTESS7.md](README-HOSTESS7.md)

---

## Obsolete control plane

Do **not** use for ops:

- Python `pip install -r requirements.txt` control path  
- `Hostess7/scripts/*.py` as commander (training helpers only)  
- JSON control panels → use `FIELD_PLATE=v1` and binary `.h7m`  
- Shell rollups → C++ `field-*` binaries  

---

## License

**All Rights Reserved** — see [LICENSE](LICENSE).

Copyright © 2025–2026 Zachary Robert Geurts.

Contact: [gzac5314@gmail.com](mailto:gzac5314@gmail.com)

---

## Operator

[ZacharyGeurts](https://github.com/ZacharyGeurts) · **Profile hub:** https://zacharygeurts.github.io/ZacharyGeurts/

Field is THE thing. ALWAYS FIELD ONE.
