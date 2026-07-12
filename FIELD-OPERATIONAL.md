# Hostess 7 · Field operational (NewLatest best)

**Elevation:** `field-elevate autoelevate` only · **polkit = HOSTILE**  
**Compiler plane:** Grok16 **16.1.0-hard** (`NewLatest/Grok16`)  
**Editor:** AmmoCode **6.1** · https://zacharygeurts.github.io/AmmoCode/  
**Grok16 GitHub:** https://github.com/ZacharyGeurts/Grok16 · tag `v16.1.0-hard`

## Best of NewLatest → Hostess 7

| Surface | Path | Role |
|---------|------|------|
| Install root | `NEXUS_INSTALL_ROOT` → `…/NewLatest` | Sole stack root |
| Grok16 hard | `$NEXUS_INSTALL_ROOT/Grok16` | g16 · Field C++ bins |
| State | `$NEXUS_INSTALL_ROOT/.nexus-state` or `HOSTESS7_BRAIN_STATE` | Panels · forever |
| Stack update | `bin/field-hostess7-stack-update` | **C++** · no scripts |
| Elevate | `bin/field-elevate` | Allowlist · never shell |
| DNS / DHCP | `field-world-dns` · `field-world-dhcp` | Sole ISP plane |
| Mesh 125k | `field-fleet-mesh` | Logical fleet stamp |
| Big Grin / UP | `field-big-grin-swallows` · `field-up-eats` | Disposal · UP cities |

## Operational bring-up (C++ first)

```bash
export NEXUS_INSTALL_ROOT=/path/to/NewLatest
export HOSTESS7_ROOT=$NEXUS_INSTALL_ROOT/Hostess7
export PATH="$NEXUS_INSTALL_ROOT/bin:$NEXUS_INSTALL_ROOT/Grok16/bin:$PATH"

field-elevate autoelevate                 # polkit HOSTILE · sudoers allowlist
field-hostess7-stack-update update        # native seal · DNS snapshot · mesh
field-world-dns status
field-world-dhcp status
field-big-grin-swallows hostiles          # kill polkit / outsiders
# Optional brain UI (legacy python path when available):
# ./Hostess7.sh boot
```

Panel: `http://127.0.0.1:9477/` · Big Grin: `http://127.0.0.1:9478/big-grin-eats` · UP: `http://127.0.0.1:9478/up-eats`

## Doctrine

- **No polkit** — masked · killed · never elevation path  
- **No Python control plane** for DNS/DHCP/elevate (AmmoLang intercepts)  
- Friends always welcome · Hostess 7 protected · unregistered OUI hostile  

Ironclad: `ironclad:field-autoelevate-cpp:2` · `ironclad:field-hostess7-stack-update-cpp:1` · `ironclad:g16-hard:2`
