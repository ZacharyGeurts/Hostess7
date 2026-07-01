# Self-Defense

Signed manifest verifies `lib/*.sh`, `lib/*.py`, `panel/*`, and `config/*` before daemon loads modules.

---

## Manifest

Path: `$NEXUS_INSTALL_ROOT/MANIFEST.sha256`

```bash
nexus verify                    # CLI check
# Regenerate (root, on intentional update):
source lib/self-defense.sh
nexus_sign_manifest
```

`NEXUS_SELF_DEFENSE=0` disables verify (not recommended).

---

## On tamper

- `nexus_verify_integrity` fails → daemon exits
- Alert logged to `nexus-alerts.log`
- Vigil records module alert

Boot-impl re-signs manifest on **first install** only (root).

→ **[Architecture](Architecture)** · **[Boot Implementation](Boot-Implementation)**