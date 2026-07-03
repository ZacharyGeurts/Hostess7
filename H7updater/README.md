# H7updater

**Official Hostess 7 software update catalog** — Layer 0 Archival Warehouse.

- **Sovereign lane:** `ZacharyGeurts/*` stack manifest (read-only public API). Only ZacharyGeurts pushes code here.
- **Personal lane:** GitHub OAuth device flow (read-only) so operators connect **their** repos the same way.

## Pages

https://zacharygeurts.github.io/H7updater/

## Manifest

| File | Purpose |
|------|---------|
| `data/h7updater-stack-index.json` | Alphabetized stacked folder index (A–Z × layer_z) |
| `data/h7updater-oauth-doctrine.json` | Sovereign vs personal OAuth lanes |
| `data/h7updater-version.json` | H7updater product version |

Rebuild manifest from live GitHub:

```bash
python3 scripts/build-stack-index.py
```

## Folder doctrine

```
stack/{LETTER}/{RepoName}/
```

- **LETTER** = first character of repo name (A–Z, else `#`)
- **layer_z** = stack depth (−4 Hostess7 brain → 0 warehouse → 3 satellites)

## Personal GitHub (read-only)

1. Create a [GitHub OAuth App](https://github.com/settings/applications/new) with **Device flow** enabled.
2. Scopes: `read:user`, `repo:read` only — no write to ZacharyGeurts.
3. Open Pages → **Your GitHub** lane → paste Client ID → **Authorize**.

## Wire into field

- Archival Warehouse: `panel/ammoos-warehouse.html` fetches this manifest.
- Local apply: `/ammoos-update-os` (AmmoOS Software Update Manager).

## License

All Rights Reserved — ZacharyGeurts.