# GNU EOL Terminal — Full Operator Manual

**GNUEOLTerminal** is the Field Tech terminal for Hostess7: shell ≡ terminal, iron plate witness, optional combinatronic, and the Classic Schooler wiki built in.

> Grok impersonates Richard Stallman in the **textbook prose** — disclosed in the preface. This manual cites **implemented** code paths only.

## 1. What this is

- **GNU EOL Terminal** — last terminal software the world needs; themeable, tight paneling, GNU options restored
- **Field GNU Terminal** — Python dispatch shell (`lib/field-gnu-terminal.py`) behind panel :9477
- **Iron plate** — `field-gnu-terminal-iron-plate.py` — plate meld, chain hash, Ironclad read-first
- **Classic Schooler wiki** — Emacs · Bash · coreutils · Field Technology v5 (22 chapters)
- **MS-DOS 4.0 host** — `modules` · `load-module` · MSPaint · EDIT · MEM

**Doctrine:** Shell and terminal are the same surface. Combinatronic is optional. Plate meld never lies.

## 2. Live surfaces

- **Textbook (home)** — https://zacharygeurts.github.io/GNUEOLTerminal/
- **This wiki** — https://zacharygeurts.github.io/GNUEOLTerminal/wiki/
- **Field Tech terminal** — https://zacharygeurts.github.io/GNUEOLTerminal/terminal/
- **AmmoOS desktop** — https://zacharygeurts.github.io/Hostess7/desktop/
- **EOL Code panel** — https://zacharygeurts.github.io/Hostess7/eol-code/

**Local loopback (sovereign stack):**

```text
http://127.0.0.1:9477/field-gnu-terminal-embed.html
http://127.0.0.1:9477/api/field-gnu-terminal
http://127.0.0.1:9477/terminal/
```

**Aliases:** `terminal` · `gnu-terminal` · `shell` · `gnueol`

## 3. Boot order

1. Start field stack: `AML_BUILD=0 bash scripts/impl/start-field-stack.sh`
2. Panel :9477 serves embed + API
3. Optional Queen :9481 for RTX browser shell
4. Type `wiki` in the terminal → opens Classic Schooler wiki map

Pages mirror (no local stack): use GitHub Pages terminal URL above — same JS, API shim to static JSON.

**Hostess7 train-up (before Pages publish):**

```bash
bash scripts/hostess7-full-train.sh          # corpus + combinatronic refresh
bash Hostess7/scripts/hostess7-pre-update.sh # AML boundary preflight
./Hostess7.sh pages-publish                  # surfaces + GNUEOL wiki mirror
```

The terminal does not replace this train — it **witnesses** the same stack the wiki documents. If `help` works but `wiki` URLs 404, the book build did not run; see §17.

## 4. Pages runtime vs loopback

On **GitHub Pages**, the terminal embed uses `api-shim.js` to serve static JSON snapshots when loopback `:9477` is unreachable. Same JS bundle (`field-gnu-terminal.js`) — only the transport changes.

On **loopback**, every command hits live `POST /api/field-gnu-terminal` with sovereign gate + iron plate chain.

**Rule:** develop on loopback; publish to Pages; verify both with `wiki` command URLs.

## 5. Terminal UI

### 5.1 Widgets

See [Widgets & tight paneling](widgets-and-paneling.md):

- Tab strip (multi-session, split ≤4)
- Code preview sidebar (live source beside stderr)
- Scroll thumb (touch + drag)
- Theme picker (AmmoOS C2 themes API)
- Mini-browser proxy (`/browse/view`)
- Status bar (cwd · kernel · CLI family)

### 5.2 Themes

Default: `black_emerald_rose_2026` · Mono: `mono_terminal`

API: `GET /api/ammoos-themes` · client applies via `field-gnu-terminal.js`

### 5.3 Menus

File · Edit · View · Options · Help — same families as classic GNU terminal expectations.

## 6. Command reference

Commands route through `POST /api/field-gnu-terminal` with body `{ "action": "run", "command": "...", "cwd": "..." }`.

### 6.1 Built-in Field commands

- `help` — KILROY Universal CLI index (POSIX · GNU · BSD · CMD · PowerShell · KILROY)
- `wiki` — print GNUEOL wiki URLs (book + classic schooler topics)
- `field-tech` — same as `wiki`
- `clear` — clear terminal buffer
- `cd <dir>` — change cwd within KILROY_ROOT + SG_ROOT only
- `kernel` — KILROY Field OS kernel witness (`/proc/kilroy_field/*`)
- `kilroy` / `kilroy-status` — KILROY stack status
- `truth` — Ironclad truth floor (`field-ironclad-truth.py`)
- `truth diagnostic` — diagnostic truth mode
- `discern <text>` — stress/terror discern (`field-stress-terror-discern.py`)
- `combinatorics` — combinatronic bridge status (optional engine)
- `combinatronic` — alias
- `g16-combinatronics` — alias
- `bash -c combinatorics` — inner combinatronic dispatch

### 6.2 MS-DOS 4.0 module host

- `modules` — list loadable DOS 4.0 modules
- `load-module <name>` — load module (opens surface URL)
- `mspaint` / `paint` — MSPaint at `/mspaint` (PCX · clipboard)
- `edit` — MS-DOS Editor (GNU Terminal embed)
- `mem` — stack witness → `truth memory`
- `gwbasic` / `basic` — coming soon (CHIPS lane)

Right-click AmmoOS desktop → **Load DOS 4.0 module…**

### 6.3 Allowed POSIX / toolchain (allowlist)

Core: `ls` `pwd` `echo` `cat` `head` `tail` `grep` `find` `wc` `whoami` `date` `env` `which` `file` `stat` `tree` `du` `df` `uname`

Build: `g16` `g16-gcc` `g16-g++` `g16-as` `g16-ld` `g16-objdump` `g16-nm` `gpy-16` `pythong` `python3` `git` `make` `bash` `sh`

Field: `kilroy` `ammolang-run.sh` `export` `rg` `locate`

CMD aliases: `dir` `type` `cls` `copy` `del` `md` `chdir` `ver` `where` `findstr`

Scripts: `./foo.sh` and `./foo.py` under field roots only.

**Blocked:** `rm -rf /`, `mkfs`, `dd if=`, `curl | sh`, shutdown/reboot — see dangerous-command guard in `field-gnu-terminal.py`.

### 6.4 Wiki command output

```text
wiki
```

Returns:

```text
Field Tech Terminal — GNUEOL Classic Schooler Wiki
  book:  https://zacharygeurts.github.io/GNUEOLTerminal/
  wiki:  https://zacharygeurts.github.io/GNUEOLTerminal/wiki/
  topics: emacs · bash · coreutils · ssh · gpl · field-tech
```

## 7. HTTP API

### 7.1 Terminal dispatch

```http
POST /api/field-gnu-terminal
Content-Type: application/json

{"action": "run", "command": "help", "cwd": "/path/to/kilroy"}
```

```http
GET /api/field-gnu-terminal
```

Returns `field-gnu-terminal/v2` status: cwd, themes, kernel slice, universal CLI doctrine, DOS 4.0 flag.

### 7.2 Related APIs

- `/api/field-dos40` — MS-DOS 4.0 module list
- `/api/ammoos-themes` — theme catalog
- `/api/sovereign-time` — linear clock · slowdown ≥800ms = threat
- `/browse/view` — mini-browser proxy
- `/api/field-eol-code` — EOL Code BSP tree (Layer 0 paths)
- `/api/field-legacy-connect` — legacy open + secured posture · Dreamcast modem slice
- `/api/field-botnet-dns-dhcp` — Truth DNS + Field DHCP + GitHub control plane
- `/api/field-dns-drift-threat` — DNS drift threat panel · servers_updated audit
- `/api/field-github-legacy` — GitHub legacy secure lane (old browsers welcome)

### 7.3 Iron plate panel

Written to `.nexus-state/field-gnu-terminal-iron-plate-panel.json` on plate meld refresh.

Doctrine: `data/field-gnu-terminal-iron-plate-doctrine.json`

## 8. Iron plate & security

**Policy (iron plate doctrine):**

- `shell_terminal_identical`: true
- `combinatronic_optional`: true
- `plate_meld_required`: true
- `ironclad_read_first`: true
- `fsync_panel`: true
- `chain_hash`: true

**Chain:**

```text
field-gnu-terminal-embed.html
  → /api/field-gnu-terminal
  → kilroy-universal-shell + allowlist
  → field-gnu-terminal-iron-plate.py
  → field-plate-meld.py (chain hash)
  → field-ironclad-truth.py (truth command)
  → field-gnu-identity-verify.py (rms @ GitHub 10550344)
```

**Truth command** witnesses plate meld, GNU terminal posture, and diagnostic queries. Use before arguing with stderr.

## 9. EOL Code integration

EOL Code (`lib/field-eol-code.py`) maps the Field stack BSP tree from pending (−4) to EOL at Layer 0. GNU Terminal is an EOL marker node.

- Panel: `/eol-code/` on Hostess7 Pages
- Local: `python3 lib/field-eol-code.py panel`
- AML: `library/dewey/000-computer-science/ammolang/eol_code.aml`

Terminal paths under KILROY + SG appear in the EOL tree when generator has run.

## 10. Entropy grade & sovereign time

Production panels must agree: stderr, jsonl, sovereign time, panel latency.

```bash
curl -s http://127.0.0.1:9477/api/sovereign-time | jq .derived_utc
grep THERMO ~/.nexus-state/*.jsonl | tail
```

See [Entropy grade production](entropy-grade.md) and [Sovereign time](sovereign-time.md).

## 11. RTX panels

When `queen_rtx` permit gates open (Grok16 / AMOURANTHRTX), RTX widgets unlock. CPU `field_opt` path keeps same UI — gated tools hidden.

See [RTX panels](rtx-panels.md).

## 12. Classic Schooler wiki map

- Overview — [GNU Technical Manual](gnu-technical-manual.md)
- Emacs — [emacs](emacs.md)
- Bash — [bash](bash.md)
- Coreutils — [coreutils](coreutils.md)
- SSH — [ssh](ssh.md)
- GPL — [gpl](gpl.md)
- Field Tech — [field-tech](field-tech.md)

## 13. Field Technology primer (22 chapters)

Full primer from `Textbook/field-technology-v5.txt`:

1. [Ch 01 · Read this before you dispatch anything](ft-ch01-read-this-before-you-dispatch-anything.md)
2. [Ch 02 · Learning objectives](ft-ch02-learning-objectives.md)
3. [Ch 03 · Learning objectives](ft-ch03-learning-objectives.md)
4. [Ch 04 · Learning objectives](ft-ch04-learning-objectives.md)
5. [Ch 05 · Learning objectives](ft-ch05-learning-objectives.md)
6. [Ch 06 · Learning objectives](ft-ch06-learning-objectives.md)
7. [Ch 07 · Offensive Dispatch — GPU Field Engine](ft-ch07-offensive-dispatch-gpu-field-engine.md)
8. [Ch 08 · Die-Resident Universe](ft-ch08-die-resident-universe-field-die-data-bus.md)
9. [Ch 09 · Stability Under Load — FCC & Tesla](ft-ch09-stability-under-load-fcc-tesla.md)
10. [Ch 10 · Hardware Spiderweb](ft-ch10-hardware-spiderweb-sub-micron-mirror.md)
11. [Ch 11 · Observability](ft-ch11-observability-reading-the-battlefield.md)
12. [Ch 12 · Reality vs Theory — The Rocks](ft-ch12-reality-vs-theory-the-rocks.md)
13. [Ch 13 · Thermodynamic receipts](ft-ch13-creditor-deep-dive-thermodynamic-receipts.md)
14. [Ch 14 · Shannon Oracle](ft-ch14-creditor-deep-dive-shannon-oracle.md)
15. [Ch 15 · Maxwell GPU](ft-ch15-creditor-deep-dive-maxwell-gpu.md)
16. [Ch 16 · Love Coupling](ft-ch16-sacred-long-form-love-coupling.md)
17. [Ch 17 · God Boundary](ft-ch17-sacred-long-form-god-boundary.md)
18. [Ch 18 · Operator Covenant](ft-ch18-sacred-long-form-operator-covenant.md)
19. [Ch 19 · Sovereign time](ft-ch19-introduction-why-sovereign-time-exists.md)
20. [Ch 20 · Terror-threat posture](ft-ch20-introduction-public-services-under-terror-threat-posture.md)
21. [Ch 21 · Queen doctrine](ft-ch21-introduction-queen-doctrine.md)
22. [Ch 22 · Glossary v5](ft-ch22-glossary-field-technology-v5.md)

## 14. Troubleshooting

### 14.1 Terminal dispatch

- `blocked: 'foo' not in field allowlist` — command not in ALLOWED_BASES; use `help` or extend allowlist in `field-gnu-terminal.py`
- `cd: outside field roots` — cwd must stay under KILROY_ROOT + SG_ROOT
- `truth module unavailable` — ensure `lib/field-ironclad-truth.py` present; run plate meld
- `discern module unavailable` — `lib/field-stress-terror-discern.py` missing
- Panel 503 on API — stack not up; start `AML_BUILD=0 bash scripts/impl/start-field-stack.sh`
- Themes empty — check `data/ammoos-themes-doctrine.json`
- GW-BASIC — `coming_soon`; CHIPS lane not wired yet
- Slow API — check sovereign-time; ≥800ms logs threat witness

### 14.2 Wiki / Pages

- **Full manual 404** — run `python3 scripts/build-site.py` then `verify-gnu-wiki-manual.py`
- **Wiki index missing link** — re-run `forge-gnu-wiki-manual.py` (preserves `eol-terminal-full-manual.md`)
- **Hostess7 mirror stale** — `./Hostess7.sh pages-publish` rebuilds `docs/gnueol-terminal/`
- **github.com slow** — use Pages mirror URLs in §2; `pages-github-legacy-wire.js` on Hostess7

### 14.3 DNS / legacy connect

- `takeover_phase: observing` — run `./scripts/legacy-connect-primary.sh` (needs Truth DNS healthy)
- `truth_up: false` — port 53 needs root or `CAP_NET_BIND_SERVICE`; check `field-dns-serve.log`
- Dreamcast BBA no DNS — confirm DHCP option 6 is queen LAN IP (`192.168.47.1`), not `127.0.0.1`
- Dreamcast dial-up — check serial device in `field-legacy-connect` panel; use generated `dreamcast-modem.peer`
- `DNS_DRIFT_THREAT` — run `./scripts/dns-clean-tables.sh clean` (not `clear` unless you know)

### 14.4 Verify before you claim done

```bash
cd GNUEOLTerminal
python3 scripts/verify-gnu-wiki-manual.py && echo OK
```

Exit `0` means: source manual, built HTML, index link, 22 ft-chapters, and topic needles all present.

## 15. Hostess7 stack update (operator)

EOL Terminal rides the **Hostess7 Field stack**. Update order:

```bash
# 1 — Truth DNS before any git push (sovereign path)
./scripts/github-unflake.sh audit --apply

# 2 — Legacy open + secured primary (Dreamcast · retro LAN welcome)
./scripts/legacy-connect-primary.sh

# 3 — Full Hostess7 Pages surfaces (includes GNUEOL wiki mirror)
cd Hostess7 && ./Hostess7.sh pages-publish

# 4 — Source repo push (when ready)
./Hostess7.sh github-secure publish
# or from repo root:
bash scripts/publish-hostess7-github.sh --push
```

**Pages mirrors after publish:**

| Surface | URL |
|---------|-----|
| Hostess7 desktop | https://zacharygeurts.github.io/Hostess7/desktop/ |
| GNUEOL textbook | https://zacharygeurts.github.io/GNUEOLTerminal/ |
| **This wiki** | https://zacharygeurts.github.io/GNUEOLTerminal/wiki/ |
| GNUEOL on H7 mirror | https://zacharygeurts.github.io/Hostess7/gnueol-terminal/wiki/ |
| EOL Code panel | https://zacharygeurts.github.io/Hostess7/eol-code/ |
| Botnet DNS/DHCP | `/api/field-botnet-dns-dhcp` on Hostess7 Pages |

`hostess7_pages_surfaces_build.py` runs `forge-gnu-wiki-manual.py` + `build-site.py` before copying `GNUEOLTerminal/docs` → `Hostess7/docs/gnueol-terminal/`.

## 16. Legacy open + secured (DNS · DHCP · Dreamcast)

**Forever policy:** modern stack goes **primary**; retro gear keeps **open ears** through the **secured gatekeeper**.

| Role | Authority |
|------|-----------|
| GitHub | Control-plane tables + doctrine (120s sync) |
| `field-dns.py` | Truth resolver @ `127.0.0.1:53` (RFC 1035 classic for retro) |
| `field-dhcp.py` | Leases; retro pool `192.168.47.100–150` for Sega OUIs |
| Dreamcast BBA DNS | Queen LAN `192.168.47.1` (not loopback — console cannot use 127.0.0.1) |
| Dreamcast dial-up | PPP peer `.nexus-state/dreamcast-modem.peer` · `pppd call dreamcast-modem` |

**Operator commands:**

```bash
./scripts/legacy-connect-primary.sh
python3 lib/field-legacy-connect.py json
python3 lib/field-dns-drift-threat.py servers
./scripts/dns-clean-tables.sh clean
```

**APIs:** `/api/field-legacy-connect` · `/api/field-legacy-connect-primary` · `/api/field-dns-drift-threat`

**Terminal wiki command** still prints GNUEOL URLs; DNS/DHCP status is on Hostess7 panel APIs when the stack is up.

## 17. Build & publish wiki

From `GNUEOLTerminal/`:

```bash
python3 scripts/forge-gnu-wiki-manual.py   # wiki/*.md (preserves eol-terminal-full-manual.md)
python3 scripts/forge-book.py              # textbook chapters
python3 scripts/build-site.py              # markdown → docs/*.html
python3 scripts/verify-gnu-wiki-manual.py  # must pass before publish
bash scripts/publish-github-wiki.sh      # github.com/.../GNUEOLTerminal/wiki
bash ../scripts/publish-gnueol-terminal-github.sh --push
```

**Verify checklist** (`verify-gnu-wiki-manual.py`):

- `wiki/eol-terminal-full-manual.md` exists · ≥2000 words · sections 1–17
- `docs/wiki/eol-terminal-full-manual.html` built
- `docs/wiki/index.html` links to full manual
- Field Technology chapters `ft-ch01` … `ft-ch22` present
- Hostess7 mirror path documented in manual §14

## 18. License & dedication

**GPL-3.0-or-later** when vendored from NewLatest.

Dedicated to **Richard Matthew Stallman** (`rms`, GitHub id `10550344`). Identity verify: `lib/field-gnu-identity-verify.py` pins `gnu.org` TLS.

---

**Repo:** https://github.com/ZacharyGeurts/GNUEOLTerminal · **Operator:** ZacharyGeurts · Hostess7 Field Stack

---

*This manual is the canonical operator entry for the Classic Schooler wiki. When in doubt: run `verify-gnu-wiki-manual.py`, read stderr, then `wiki` from the terminal. The book prose may impersonate RMS; the verify script does not — it only checks files that exist on disk and links that resolve in `docs/wiki/`.*