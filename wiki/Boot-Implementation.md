# Boot Implementation

Every **startup and reboot** reloads field tech before the normal daemon loop. **First install** runs a heavier path once. **v10.4.3** hardens the path for non-destructive, marker-driven operation with bounded thermal-guard redata.

---

## Flow

![Boot I/O](https://raw.githubusercontent.com/ZacharyGeurts/NEXUS-Shield/main/docs/images/io-boot-flow.svg)

1. **systemd** `ExecStartPre` → `scripts/nexus-boot-impl.sh`
2. **Validate** `NEXUS_INSTALL_ROOT` (absolute path, no traversal)
3. **First install** (`first-boot.complete` missing): wire-stack, migrate, sign manifest, **bounded thermal redata**, sense meld, training viewer
4. **Every boot** (refresh): re-wire, export paths, front-hook, verify, **bounded thermal redata** — **no** migrate, sign, or training viewer
5. **Daemon** starts watchers + panel + field-switch-safety + field-thermal-guard cycle
6. **Browser** opens `/field` once per `boot_id`

---

## Thermal guard (v10.4.3)

| Step | Behavior |
|------|----------|
| `thermal_guard_init` | `field-thermal-guard.py evaluate` — headroom + policy env |
| `bounded_redata` | `field-global-redata.py boot-test` — 3-region incremental pass |

→ **[Field Thermal Guard](Field-Thermal-Guard)**

---

## Hardening (v10.4.2+)

| Guard | Behavior |
|-------|----------|
| Trusted scripts | External scripts must resolve under install root |
| Timeouts | wire-stack, migrate, meld capped (default 30s) |
| Log rotation | `boot-impl.log` truncated when > 5 MB |
| Integrity | Failures logged explicitly — not masked with `\|\| true` |
| Python | `nexus_resolve_pythong` → `python3` fallback |

---

## Scripts

| Path | Role |
|------|------|
| `lib/nexus-boot-impl.sh` | Core first vs refresh logic |
| `scripts/nexus-boot-impl.sh` | Standalone entry (ExecStartPre) |
| `scripts/nexus-release-finalize.sh` | Pre-deploy smoke test |

Hooked from: `nexus-daemon.sh`, `nexus.sh`, `genius_shield.sh` (first install).

---

## Markers (`NEXUS_STATE_DIR`)

```
first-boot.complete    # written after first full impl
boot-impl.last         # mode=first|refresh, version, ts
boot-impl.log          # wire-stack output (rotated)
panel-launched.boot    # kernel boot_id — browser once per reboot
```

---

## Force full re-impl

```bash
sudo rm /var/lib/nexus-shield/first-boot.complete
sudo systemctl restart nexus-genius.service
```

Or one-shot: `NEXUS_BOOT_FORCE_FIRST=1 bash scripts/nexus-boot-impl.sh`

---

## Disable

Set `NEXUS_BOOT_IMPL=0` in `config/nexus.conf` or `settings.override`.

→ **[Field Switch Safety](Field-Switch-Safety)** · **[SECURITY.md](https://github.com/ZacharyGeurts/NEXUS-Shield/blob/main/SECURITY.md)**