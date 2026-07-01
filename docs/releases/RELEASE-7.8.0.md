# NEXUS-Shield 7.8.0 — Field Radio Quality · Standalone · Field Drive Tools

## Field radio receiver

- **Crest · spectral flatness · RMS** — unified `analyze_audio_quality()` in demod pipeline; program audio validation on catch/retry.
- **Signals tab** — hardware probe card + audio quality panel (crest, flatness, dBFS, PROGRAM verdict).
- **3-field receiver** — Gladstone / Escanaba / Iron Mountain; WIMK 93.1 retry until program audio.

## Field standalone (no sudo from tree)

- **`./nexus.sh`** — uses `.nexus-state/` for logs and state; no `/var/log` permission errors.
- **`field-hardware-probe.py`** — USB/net/audio/tools via sysfs/proc; no root required.
- **Field tools registry** — `lib/bin` tools publish to `nexus-field/tools/` on field drive.

## Updater

- **UPDATE NOW** — git pull + `stealth_install.sh` from source tree; update lock prevents mid-install breaks.
- **`nexus-update.py`** — compares local `NEXUS_VERSION` to GitHub releases/latest.

Install from tree: `./nexus.sh --no-browser` (no sudo) or `sudo ./stealth_install.sh` (system install).  
Panel: https://127.0.0.1:9477/field