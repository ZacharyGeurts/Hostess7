# Configuration

Two layers: **shipped defaults** and **runtime overrides**.

---

## Files

| File | Role |
|------|------|
| `config/nexus.conf` | Shipped defaults (640 root:nexus) |
| `$NEXUS_STATE_DIR/settings.override` | Panel-written toggles |
| `config/device-whitelist.conf` | Sacred IPs / devices |

Restart after manual `nexus.conf` edits:

```bash
sudo systemctl restart nexus-genius.service
```

Panel settings apply immediately to override file — daemon reads on vigil cycle.

---

## Key defaults (v10.4.3)

| Variable | Default | Meaning |
|----------|---------|---------|
| `NEXUS_THREAT_PANEL` | 1 | Panel HTTP server |
| `NEXUS_PANEL_AUTO_OPEN` | 1 | Browser on boot |
| `NEXUS_NO_OS_BROWSER_HOOK` | 0 | Allow OS browser fallback |
| `NEXUS_BOOT_IMPL` | 1 | Boot tech reload |
| `NEXUS_NETWORK_LOCKDOWN` | 0 | Off for everyday users |
| `NEXUS_UNDERLAY_HOTKEY` | 1 | F9 Tristate hotkey |
| `NEXUS_FIELD_THERMAL_GUARD` | 1 | Landauer work budget + incremental redata |
| `NEXUS_FIELD_MAX_JOULES_PER_SEC` | 45 | Conservative TDP headroom |
| `NEXUS_FIELD_REDATA_CHUNK` | 8192 | Tiles per incremental redata pass |

---

## Environment

```bash
export NEXUS_STATE_DIR=/var/lib/nexus-shield
export NEXUS_INSTALL_ROOT=/usr/local/lib/nexus-shield
export NEXUS_THREAT_PANEL_PORT=9477
export SG_ROOT=/path/to/NewLatest
```

→ **[Panel Guide](Panel-Guide#settings)** for UI toggles.