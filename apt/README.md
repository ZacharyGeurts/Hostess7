# Hostess 7 Field apt tree

**Sole package origin for Spear Field OS.**

| Item | Value |
|------|--------|
| Distribution | `field` |
| Component | `main` |
| Arch | `amd64` |
| Pages URL | https://zacharygeurts.github.io/Hostess7/apt/ |
| Git URL | https://github.com/ZacharyGeurts/Hostess7/tree/main/apt |

## Operator (on Spear)

```bash
field-apt update
field-apt install <pkg>
field-apt sources
```

Mint / Ubuntu / Debian apt nets are **disabled** on Spear. Only this tree is allowed.

## Layout

```text
apt/
  dists/field/main/binary-amd64/Packages
  dists/field/main/binary-amd64/Packages.gz
  pool/main/…   # .deb packages land here
  README.md
```

## Adding a package

1. Build a `.deb` for Field / Spear / Hostess7 components only.  
2. Place under `pool/main/<name>/`.  
3. Regenerate `Packages` + `Packages.gz`.  
4. Push `main` (and gh-pages mirror if Pages uses that branch).

```bash
# from Hostess7 repo root
./apt/regen-index.sh
```

God Bless.
