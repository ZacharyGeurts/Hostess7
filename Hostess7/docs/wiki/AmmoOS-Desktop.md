# AmmoOS Desktop · Field One

**AmmoOS** is the classic field desktop OS surface for Hostess 7 — Start menu, icons, plated stack (NEXUS C2 → Ironclad → KILROY iPXE → DNS/DHCP), AmmoNet Cloud.

## Live surfaces

| Surface | URL |
|---------|-----|
| **GitHub Pages OS (canonical)** | https://zacharygeurts.github.io/Hostess7/desktop/ |
| **Local AmmoOS (C++)** | http://127.0.0.1:9477/field |
| **AmmoOS manual hub** | https://zacharygeurts.github.io/AmmoOS/ |
| **Hostess 7 hub** | https://zacharygeurts.github.io/Hostess7/ |
| **Status plate** | http://127.0.0.1:9477/api/status |
| **Stack plate** | http://127.0.0.1:9477/api/stack |

## Control plane (C++ only)

```bash
# From NewLatest / Hostess7 package root
./bin/field-ammoos online     # update stack + serve :9477/field
./bin/field-ammoos status
./bin/field-ammoos update
./bin/field-hostess7 online   # full Hostess7 + AmmoOS bring-up
./bin/field-hostess7 ammoos   # AmmoOS only
```

Rebuild:

```bash
make -C native/field-tools field-ammoos
```

**No shell / no Python control.** `field-ammoos` is the ops entry. Plates under `.nexus-state/field-ammoos.plate`.

## Full stack layers

1. Hardware  
2. NEXUS C2 (layer −3, IRQ/DMA)  
3. Ironclad BSP  
4. KILROY iPXE  
5. World DNS + DHCP mesh (125k doctrine)  
6. **AmmoOS classic desktop** ← this page  
7. Queen Browser `:9481`  
8. Hostess 7 multibrain (32 · RAID-0 · shared redundant)

## Package

NewLatest **is** the Hostess 7 package. AmmoOS desktop assets live in `panel/` (local) and `Hostess7/docs/desktop/` (Pages).

See also: [[Getting-Started]] · [[Internet-Stack]] · [[Hostess7-Senses]] · [[Distributed-Cloud-H7r]]
