# AmmoCode 6.1 — Stack Editor

**Lean sovereign code editor** — opens **any text file from any era**, runs on **g16**, zero telemetry, loopback only.

Part of the [AmmoOS stack](https://github.com/ZacharyGeurts/AmmoOS/blob/main/STACK-NAV.md).

```bash
python3 ammocode.py
# → http://127.0.0.1:9555/
./scripts/ammocode-open.sh /path/to/file.txt
```

## Text-era open

AmmoCode reads the canonical **268-extension** filetype DB (`field-programming-filetypes.json`):

| Era | Examples | Encoding |
|-----|----------|----------|
| Modern | `.ts`, `.py`, `.rs`, `.md` | UTF-8 |
| DOS / BBS | `CONFIG.SYS`, `AUTOEXEC.BAT`, `.nfo`, `.ans` | CP437 / Latin-1 |
| Legacy langs | `.bas`, `.f90`, `.cob`, `.pas`, `.prg` | Latin-1 ladder |
| Plain | `.txt`, `.log`, `.lst`, `.tex` | Auto-detect |

Binary guard rejects `.exe`, images, archives — unless extension is in the programming DB.

**Discern:** `g16 --g16-discern` → syntax highlight + Run/Build actions.

## Non-destructive

AmmoCode **never destructively writes** itself or the outside world:

| Rule | Behavior |
|------|----------|
| Disk API | Read-only — no `write_file` / `save_file` / `delete` |
| Save | **Export** (browser download) — operator picks destination |
| Read jail | home, SG, AmmoOS, `/tmp` |
| Run jail | Blocked inside AmmoCode tree and system paths |
| Settings | Only `~/.config/ammocode` and `.nexus-state/ammocode` |

Doctrine: `data/ammocode-nondestructive-doctrine.json`

## Toolbar (v2 — no bloat)

Essentials only: file · edit · g16 check/build/run · discern · themes · settings.

Removed vestigial stubs professionals never use: minimap, split editor, breadcrumbs, collab theater, screenshare, git status placeholder, print, save-all, format stub.

## Surfaces

| URL | Role |
|-----|------|
| http://127.0.0.1:9555/ | Stack editor |
| http://127.0.0.1:9555/?file=/path | Open path via API |

Settings: `~/.config/ammocode/ammocode-settings.secure.json`

## Pairing

| Component | Version |
|-----------|---------|
| Grok16 | 5.1.0 · `g16` @ 16.2.0 |
| AmmoOS | 2.0.0-beta4 |
| Filetypes | `NewLatest/data/field-programming-filetypes.json` |

## License

Ships with AmmoOS stack.