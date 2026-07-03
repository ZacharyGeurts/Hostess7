# Hostess7 3.1.0-beta — Perf + visibility

**Stack:** NewLatest → Hostess7 · AmmoOS · GNUEOLTerminal  
**Tag:** `v3.1.0-beta`  
**Pages:** https://zacharygeurts.github.io/Hostess7/

## Highlights

### Perf (eval 8.7 → 9.5 track)
- **`./Hostess7.sh profile`** — stack ping witness + CPU/thermal + error counts
- **`./Hostess7.sh lite on`** — opt-in throttle; NEXUS + war posture **unchanged**
- **Boot watchdogs** — per-step timeouts; failures land in central log

### UI
- **Error dashboard** — `/api/field-error-dashboard` on :9477 and :9481
- **Performance flyout** — unchanged; pair with error dashboard for full visibility

### Docs
- **CHANGELOG.md** — single consolidated ledger (UI / Perf / Bug sections)

## Verify

```bash
./Hostess7/Hostess7.sh profile
./Hostess7/Hostess7.sh lite status
curl -s http://127.0.0.1:9477/api/field-error-dashboard | jq .counts
python3 lib/field-performance-flyout.py json | jq .schema
```

## Migration from 3.0.7-beta5

Lite mode is **off by default**. Enable only when you need UI responsiveness:

```bash
./Hostess7/Hostess7.sh lite on
./Hostess7/Hostess7.sh boot
```

Disable to restore full senses/training polling:

```bash
./Hostess7/Hostess7.sh lite off
```