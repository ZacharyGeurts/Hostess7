# Field DNS · Internet Field · True Reality Model

## Why DNS showed STOPPED

Three bugs blocked the Truth Resolver:

1. **Query parser crash** — `_read_name()` used `decode("idna", errors="replace")`, which raises `UnicodeError` on the first UDP query. The listener thread died; port 53 stayed bound but never answered.
2. **Duplicate serve processes** — `nexus_field_dns_serve_loop` respawned every 5s without a PID lock. Multiple zombies fought for `127.0.0.1:53`.
3. **resolv.conf not overridden** — `/etc/resolv.conf` still pointed at `127.0.0.53` (systemd-resolved), not NEXUS `127.0.0.1`. Binding `127.0.0.53` also conflicts with systemd-resolved.

### Fixes shipped

| Fix | File |
|-----|------|
| ASCII label decode + thread-safe query handler | `lib/field-dns.py` |
| Single-instance PID lock in `serve()` | `lib/field-dns.py` |
| Default bind `127.0.0.1` only (not `.53`) | `lib/field-dns.py`, `lib/field-dns.sh` |
| Internet field puller | `lib/dns-internet-field.py` |
| Hourly passive TLD pull loop | `lib/nexus-daemon.sh` |

### Restart after deploy

```bash
sudo pkill -f 'field-dns.py serve' || true
sudo systemctl restart nexus-genius
dig @127.0.0.1 example.com +short
```

Panel: https://127.0.0.1:9477/field#dns

---

## True Reality Model (WHOLE + LOCAL NOW)

Your diagram maps directly onto DNS field storage:

| Panel side | DNS meaning |
|------------|-------------|
| **WHOLE TIMELINE AT ONCE** | Every IANA TLD slot exists in `dns-internet-field.json` — all permitted delegation points held in field storage whether or not queried yet. |
| **LOCAL NOW — ACTIVE PHYSICS** | Truth resolver cache + live `dig +trace` probes mark **recognized** slots with strength %. Silent slots remain at 0% until seen. |

We hold the full internet **passively in fields** — not by downloading every hostname (impossible), but by enumerating every **TLD delegation slot** from root and merging LOCAL NOW observations as they occur. That is passive everywhere-at-once: the whole delegation tree is present; activity lights up slots.

---

## Internet field pull

```bash
# One-shot build (seed + cache, no live probes)
NEXUS_INSTALL_ROOT=/path/to/NEXUS-Shield NEXUS_STATE_DIR=/var/lib/nexus-shield \
  pythong lib/dns-internet-field.py build

# Full pull with live trace probes (48 TLD apex samples per cycle)
pythong lib/dns-internet-field.py pull
```

Output: `/var/lib/nexus-shield/dns-internet-field.json`

Fields:
- `total_slots` — every TLD in field
- `recognized_slots` — answered by cache or live trace
- `silent_slots` — held but not yet seen
- `coverage_pct` — recognized / total

Daemon pulls hourly via `nexus_dns_internet_pull_loop` (`NEXUS_DNS_INTERNET_PULL_INTERVAL=3600`).

---

## Field antenna (signals) — same pattern

RF frequency registry (`frequency_registry` in `field-rf-sentinel.py`) uses the identical model: every FCC-permitted channel slot with strength 0 when silent, recognized when AP seen. Signals tab renders this as a rippling green 3D field sheet.

---

## Theme

Buttons and text boxes: **black background (#000), white text (#fff)** — `nexus-theme.css`, `dusty-midnight.css`, `threat-panel.html`.