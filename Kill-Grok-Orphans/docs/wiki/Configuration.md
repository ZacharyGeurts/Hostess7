# Configuration

Default path: `/etc/kgo/kgo-patterns.json`

Override with `KGO_CONFIG` env var or `-c` flag.

## Schema

```json
{
  "version": "1.0.0",
  "patterns": [
    {
      "id": "grok-firmware-audit",
      "match": "grok-firmware-audit.sh",
      "reason": "Stale grok-firmware-audit orphan"
    },
    {
      "id": "grok16-awk-wrapper",
      "match": "Grok16/bin/awk",
      "reason": "Runaway Grok16 awk bash wrapper"
    },
    {
      "id": "grok16-bin-bash",
      "match": "Grok16/bin/",
      "shell_only": true,
      "reason": "Orphaned Grok16 bin bash shim"
    }
  ],
  "interval_sec": 5,
  "grace_sec": 3
}
```

## Fields

| Field | Type | Description |
|-------|------|-------------|
| `patterns[].id` | string | Identifier for logs |
| `patterns[].match` | string | Substring match on cmdline |
| `patterns[].shell_only` | bool | Only match if cmdline looks like a shell |
| `patterns[].reason` | string | Log message when killed |
| `interval_sec` | int | Scan period (daemon mode) |
| `grace_sec` | int | Seconds between SIGTERM and SIGKILL |

After editing, restart the service:

```bash
sudo systemctl restart kgo   # Linux
```