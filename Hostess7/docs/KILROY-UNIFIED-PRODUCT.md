# KILROY — Unified Product

**One product. Three faces. Internet 2.0 on boot.**

| Face | Role | Artifact |
|------|------|----------|
| **Kernel** | Field kernel (Taco) | `KILROY-bzImage` |
| **iPXE** | Netboot umbilical | `kilroy.ipxe`, `*.kpxe`, virtio ROM |
| **NEXUS C2** | Basement command surface | `127.0.0.1:9477` |

`KILROY_iPXE` is a **component name**, not a second product. Merge target: `KILROY/ipxe/`.

## Boot contract

```
Power / PXE / USB
  → KILROY iPXE (same product)
  → KILROY bzImage
       cmdline: field=1 loopback=1 i2=1 secure_layer=1 c2=9477 c2_bind=127.0.0.1
       → Secure Layer seal
       → Internet 2.0 attach (truth DNS + wire)
       → NEXUS C2 basement
       → Guest grant (AmmoMint / Mint) optional
```

Script: [`boot/kilroy.ipxe`](../boot/kilroy.ipxe)

## Internet 2.0

Booting KILROY **is** connecting to Internet 2.0. Legacy clearnet is a grant.

```bash
NEXUS_INSTALL_ROOT=/path/to/NewLatest \
  python3 lib/kilroy-i2-attach.py attach

python3 lib/kilroy-i2-attach.py status
python3 lib/kilroy-i2-attach.py guest-grant   # before AmmoMint network
```

Doctrine: `data/internet-2.0-doctrine.json`

## Secure Layer

Enforcement face of I2 on the die (not a separate product).  
Doctrine: `data/secure-layer-doctrine.json`

## NEXUS C2 harden

```bash
python3 lib/nexus-c2-harden.py status
python3 lib/nexus-c2-harden.py seal operator
export NEXUS_C2_OPERATOR_TOKEN='…'   # required for destructive actions
python3 lib/nexus-c2-harden.py authorize KILL GATE_KILL
```

Doctrine: `data/nexus-c2-harden-doctrine.json`

## Merge plan (repos)

1. **Done:** doctrines, boot script, C2 harden, I2 attach  
2. **Next:** move `KILROY_iPXE` tree → `KILROY/ipxe`  
3. **Next:** single GitHub release with kernel + iPXE + `SHA256SUMS` + GPG  
4. **Then:** README of KILROY_iPXE becomes redirect/component notice  

## Related

- `data/kilroy-unified-product-doctrine.json`
- `FIELD-DNS-INTERNET.md`
- Hostess 7 field stack · AmmoMint guest-after-I2
