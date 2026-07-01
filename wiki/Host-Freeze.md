# Host Freeze

**g16 1.0** — Freeze the guest host OS in place; field slice keeps drawing on soft freeze; sovereign clock witnesses the gap on wake.

---

## Modes

| Mode | Label | Description |
|------|-------|-------------|
| `soft` | Soft freeze | Cgroup freezer on host guest slice — `nexus-field.slice` keeps running |
| `mem` | Memory sleep | ACPI S3 — full host freeze with locked state stamp |
| `disk` | Disk close | ACPI hibernate — seal host state to disk |

All modes require root (polkit `com.nexus.field.freeze`).

---

## API

```bash
curl -s http://127.0.0.1:9477/api/field-host-freeze | jq .
curl -s -X POST http://127.0.0.1:9477/api/field-host-freeze \
  -H 'Content-Type: application/json' \
  -d '{"mode":"soft","action":"freeze"}' | jq .
```

CLI bridge: `nexus-pkexec-bridge.sh run-freeze`

Boot resume runs `resume-witness` via `nexus-boot-impl.sh` — sovereign gap stamped after wake.

Handler: `lib/field-host-freeze.py` · Doctrine: `data/field-host-freeze-doctrine.json`

→ **[Boot Implementation](Boot-Implementation)**