# NEXUS-Shield v9.0.9 — Conversation UI · field inspector · minimal power

**Release date:** 2026-06-24

## Power / heat (never overheat)

- Panel refresh **15s** (was 5s) — pauses when browser tab is hidden
- **Active-tab slice fetch only** — no longer hammers 30+ API endpoints every tick
- `field-panel-parallel.py` workers capped at **8** (was 25)
- Config: `NEXUS_PANEL_REFRESH_MS`, `NEXUS_PANEL_PARALLEL_WORKERS`
- Daemon: `Nice=19`, `IOSchedulingClass=idle`, `CPUQuota=5%`

## Hostess 7 · Super Intelligence conversationalist

- Conversation-first layout: bubble transcript, composer, suggested prompts
- Modular aside: Context · Tools · Sketch · Intel

## Field Clarity inspector

- Fixed bottom-right widget: search fields, live values, tab jumps

## Upgrade

```bash
./scripts/reboot-nexus.sh
```
