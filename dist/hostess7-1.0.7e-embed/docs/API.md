# Hostess7 API (1.0.7e)

Base URL: `http://127.0.0.1:8080` (configurable via `HOSTESS7_WEB_PORT`).

## Health

```
GET /health
```

```json
{"ok": true, "service": "Hostess7", "owner": "ZacharyGeurts"}
```

## Status

```
GET /api/status
```

Stack surfaces, brain readiness, license mode, KILROY/Queen/training probes.

```
GET /api/status/full
```

Unified core supervisor + cortex state (`hostess7-core` + `brain/state`).

## Brain (single surface)

```
GET /api/brain
```

Returns core status, cohesion IQ/truth scores, and endpoint map for all components.

## Ask

```
POST /api/ask
Content-Type: application/json

{"query": "What is hearing corpus?"}
```

```json
{"ok": true, "text": "...", "query": "..."}
```

## Reflect

```
POST /api/reflect
```

Runs one daemon cycle (online learn pulse + self-brief when not in low-power mode). Stores result in `cortex.json` → `daemon_loops`.

## Teach

```
POST /api/teach
Content-Type: application/json

{"topic": "owner preference", "content": "Always truth-first."}
```

Stores in cortex `taught[]` and optionally queries brain.

## Other endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/hearing?q=` | Hearing corpus search |
| GET | `/api/library/search?q=` | H7 library search |
| GET | `/api/world?q=` | World knowledge |
| GET | `/api/videogames?q=` | Game database |
| GET | `/api/sovereign-time` | Sovereign wait status |
| GET | `/api/final-ear` | Final ear bridge |

## CLI equivalents

```bash
hostess7-core status
hostess7-core brain
curl -s http://127.0.0.1:8080/api/brain | jq .
./Hostess7.sh benchmark-iq
./Hostess7.sh open-tasks
```