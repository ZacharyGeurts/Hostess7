# KeePass-Field

Hardened offline KeePass for the Field stack — no cloud login, readable UI on every resolution.

## Use

```bash
# Panel
http://127.0.0.1:9477/field-keepass

# CLI
NEXUS_INSTALL_ROOT=NewLatest pythong NewLatest/lib/field-keepass.py json
NEXUS_INSTALL_ROOT=NewLatest pythong NewLatest/lib/field-keepass.py launch
```

## Hardening

- KeeShare / cloud sync **off**
- Browser integration **off** (no third-party autofill accounts)
- Clipboard clears in 30s, auto-lock 300s
- Screenshot protection on
- Isolated config under `NEXUS_STATE_DIR/keepass-config/`

## UI

- **10% desktop bump** baseline (`ui_scale_pct` default 110)
- Resolution tiers: compact → UHD (`data/field-keepass-ui-tiers.json`)
- RTX hosts may **drop one tier** for comfort (panel toggle)
- Qt `QT_SCALE_FACTOR` + `field-keepass.qss` + ini font size

## Platforms

| OS | Binary |
|----|--------|
| Linux | `keepassxc`, `/usr/bin/keepassxc`, Flatpak |
| macOS | `/Applications/KeePassXC.app/...` |
| Windows | `KeePassXC.exe` |

## Upstream clone (rewrite lane)

```bash
./forge/clone-upstream.sh
```