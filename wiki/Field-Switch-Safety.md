# Field Switch Safety

**v10.4.2** — Painless tech conversion when switching to field mode. No hotspots, no surprise slowdowns.

---

## Policy

| Guarantee | Detail |
|-----------|--------|
| Non-destructive | No GRUB or kernel cmdline edits |
| In-place conversion | WRDT / drive converter — same paths |
| No surprise slowdowns | Quota holds at field-max (85%) unless **thermal crit** |
| Wave shed first | Advisory heat → stop capture, USB autosuspend — not quota cuts |
| Block only at crit | Commit, reboot, WRDT defer only when peak temp hits crit |

---

## Diagram

![Field switch safety](https://raw.githubusercontent.com/ZacharyGeurts/NEXUS-Shield/main/docs/images/field-switch-safety.svg)

---

## Module

| Path | Role |
|------|------|
| `lib/field-switch-safety.py` | Preflight + daemon cycle |
| `lib/thermal-governor.py` | hwmon advisory, hotspot detection |
| `lib/field-wave-shed.py` | Shed excess draw without slowing conversion |
| `data/field-switch-safety-doctrine.json` | Policy |
| `SECURITY.md` | Boot + conversion guarantees |

---

## Config (`config/nexus.conf`)

```bash
NEXUS_FIELD_SWITCH_SAFETY=1
NEXUS_FIELD_NO_UNEXPECTED_SLOWDOWN=1
NEXUS_FIELD_MAX=1
NEXUS_THERMAL_GOVERNOR=1
NEXUS_WAVE_SHED_APPLY=1
```

---

## Verify before commit

```bash
pythong lib/field-switch-safety.py evaluate --phase=commit
./scripts/nexus-release-finalize.sh
```

Expect `conversion_ok: true`, `switch_allowed: true`, `slowdown_guard.unexpected_slowdown: false`.

---

## Related

→ **[Boot Implementation](Boot-Implementation)** · **[Underlay F9 Tristate](Underlay-F9-Tristate)** · **[Field I/O](Field-IO)**