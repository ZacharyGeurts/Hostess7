# NEXUS-Shield v9.0.1 — TLS fix (SSL RX record too long)

**Release date:** 2026-06-24

## Fix

**Browser error: `SSL RX Record too long`** — panel was serving plain HTTP while the browser opened `https://127.0.0.1:9477/field`.

Root cause: TLS cert paths were resolved *after* `chdir(panel/)`, so relative cert paths failed silently and HTTPS was never enabled.

### Changes

- `threat-panel-http.py` — resolve TLS cert/key to absolute paths **before** chdir; search `STATE_DIR`, `INSTALL/.nexus-state`, and cwd fallbacks
- Fail fast if `NEXUS_PANEL_TLS=1` but certs are missing (no silent HTTP fallback)
- `PANEL_DIR` resolved to absolute path — fixes `/field` 404 when started with relative `panel` arg
- `hostess7-idle-grow.py` — daemon log falls back to `/tmp` when state dir not writable
- TLS cert search prefers **readable** `INSTALL/.nexus-state/tls` when `/var/lib/nexus-shield/tls` is root-only
- `nexus.sh` — same readable-cert fallback for dev/field-standalone starts

## Upgrade

```bash
./nexus.sh --no-browser
# or
pkill -f threat-panel-http.py; ./nexus.sh --no-browser
```

Open **https://127.0.0.1:9477/field** — accept the local self-signed cert once.

Includes all v9.0.0 features: Always Wartime Room, idle curiosity, neural on-the-fly expand, truth ratings.