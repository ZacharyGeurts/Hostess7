# Eternal Vigil

Maintains vigil mode, prunes alerts, recomputes paranoia posture, coordinates supervisor loop in `nexus-daemon.sh`.

- **Module:** `lib/eternal-vigil.sh`
- **State:** `vigil.state`, `vigil-alerts.log`
- **Interval:** `NEXUS_VIGIL_MAINTAIN_INTERVAL` (default 3s)

Records alerts from all modules for panel Logs tab.