# NEXUS-Shield 7.7.0 — WIP Field Radio · Antenna Catch · Update Fix

## Field radio (WIP)

- **3-field antenna receiver** — Gladstone / Escanaba / Iron Mountain mesh; we are the hardware.
- **WIMK 93.1 K-Rock** — registry lock, triangulation, retry loop until program audio validates.
- **`field-antenna-catch.py`** — sole OTA play path; no synthetic demod primary.
- **`field-wave-engine.py`** — field-wave-fm/play stack; antenna-ready without dongle gate.
- **`field-world-placement.py`** — band scan, tower DB, `play_wimk_until_working`.
- **Panel** — world placement + WIMK status cards on Signals tab.

## Update button fix

- Panel **UPDATE NOW** runs `stealth_install.sh` in-tree (git pull + install), then restarts NEXUS and reloads the window.
- No GitHub-tab fallback on failed apply — shows error and keeps UPDATE retryable.
- `stealth_install.sh` shipped to `/usr/local/lib/nexus-shield/` on install.

## Kill / autokill / rekill (unchanged)

- `nexus_field_attack_kill_target`, `autokill`, `rekill_cycle`, `install_autokill` — still wired on install and vigil.

Install: `sudo ./stealth_install.sh` from source tree.  
Panel: https://127.0.0.1:9477/field