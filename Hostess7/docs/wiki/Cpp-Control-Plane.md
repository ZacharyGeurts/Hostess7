# C++ Control Plane · Hostess 7 4.0.0-cpp

Hostess 7 ops run on **native field ELFs** — not shell, not Python, not JSON control panels.

## Entry binaries

| Binary | Role |
|--------|------|
| `field-hostess7` | Package commander · boot / online / harden / brain / package |
| `field-ammoos` | AmmoOS desktop HTTP plane · `:9477/field` |
| `field-world-dns` | Sole DNS authority |
| `field-world-dhcp` | Sole DHCP authority |
| `field-fleet-mesh` | 125k mesh plane |
| `field-elevate` | autoelevate · polkit HOSTILE |
| `field-ammolang` | Python name intercept (obsolete py → AmmoLang) |
| `field-hostess7-stack-update` | Stack pulse / protect |

Aliases: `bin/hostess7`, `bin/Hostess7`, `Hostess7/Hostess7` (ELF, not `.sh` body).

## Commands

```bash
./bin/field-hostess7 package
./bin/field-hostess7 status      # FIELD_PLATE output
./bin/field-hostess7 harden
./bin/field-hostess7 brain       # 32-node RAID-0 multibrain
./bin/field-hostess7 online      # full stack + AmmoOS
./bin/field-ammoos online
```

## Plates (not JSON control)

| Plate | Meaning |
|-------|---------|
| `hostess7-field-package.plate` | Package seal |
| `hostess7-multibrain-field.plate` | 32-brain membership |
| `hostess7-multibrain.h7m` | Binary brain pin |
| `hostess7-online.plate` | Online sitrep |
| `field-ammoos.plate` | AmmoOS desktop sitrep |
| `field-one.forever` | ALWAYS FIELD ONE |

Doctrine: `docs/hostess7-distributed-package.plate`

## Policy

- ALWAYS FIELD ONE · DISALLOW OTHERS  
- All Field all day · Grok16  
- polkit = HOSTILE · elevation = `field-elevate autoelevate`  
- Distributed brain shared/redundant across our servers  

See: [[AmmoOS-Desktop]] · [[Getting-Started]] · [[Home]]
