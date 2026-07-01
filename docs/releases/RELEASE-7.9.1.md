# NEXUS-Shield 7.9.1 — Field GUI · All Data From Fields

## Field-first panel

- **`field-gui-publish.sh`** — gatekeeper, hardware, hazard onset, lethal enforcement, Hostess7 insight publish into `threat-panel.json`.
- **`POST /api/field`** — republish full field blob; panel refresh uses **`/api/field`** (not orphan APIs).
- **`./nexus.sh`** — publishes field GUI before opening browser; version-aware port fallback (9478 when system panel is stale).

## Signals tab

- Hardware, hazard onset, audio quality, catch — all from **field publish** (no separate `/api/field-hardware` fetch on paint).
- Hazard onset panel row in Signals.

## Production

- Panel tab audit keys wired: `field_command`, `field_hardware`, `lethal_enforcement`.