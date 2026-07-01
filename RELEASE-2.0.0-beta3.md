# AmmoOS 2.0.0-beta3 — CANVAS

**Tag:** `v2.0.0-beta3` · **Repo:** [ZacharyGeurts/AmmoOS](https://github.com/ZacharyGeurts/AmmoOS) · **Manual:** [zacharygeurts.github.io/AmmoOS](https://zacharygeurts.github.io/AmmoOS/) · **Stack:** [stack hub](https://zacharygeurts.github.io/ZacharyGeurts/stack.html)

## Loopback identity

When **ZNetwork** is running, AmmoOS is **`127.0.0.1`** — the sovereign field OS on loopback, not a generic browser tab. **Queen Browser** is the secured shell; **KILROY** is the field kernel; **AmmoLang** routes all build tasks.

## Stack layering

| Layer | Role |
|-------|------|
| Hardware | Witness — no breaks, coexist host desktop |
| NEXUS C2 | Command, security, defense (`:9477`) |
| ZNetwork | 100% internet pipe on loopback |
| Queen CANVAS | RTX display block |
| Queen Browser | Secured shell — `:9481` |
| AmmoOS | Field OS inside Queen — CANVAS codename |

## Beta 3 highlights

- **KILROY-first UX** — KILROY homepage, bookmarks flyout, Queen keyboard sovereignty (Ctrl+Alt+Del, Alt+Tab internal)
- **AmmoLang #1** — all field tasks via `lib/ammolang-run.sh`; adaptive timing · hang guard · freeze assist
- **Secure GitHub MCP** — AmmoLang `github` op defaults to `mcp_secure` (not raw TCP); `grok_com_github` scoped token
- **KILROY ↔ Grok16** — kernel regression `kilroy-kernel-test.sh`; `grok16_pair` 5.2.0
- **SG → NewLatest** — canonical tree; stack siblings materialized in release tarballs
- **ZNetwork Hub** — `/field-znetwork` with Hostess 7 wire and live relayer posture
- **MCP publish layer** — `ammoos-mcp-layer.json` + `github-mcp-stdio.sh` for releases and Pages

## Pairings

| Component | Version |
|-----------|---------|
| Grok16 | 5.2.0 |
| KILROY | 1.0.0 Taco |
| ZNetwork | 2.1.0 |
| Kill-Grok-Orphans | 1.1.0 |

## Surfaces

| URL | Role |
|-----|------|
| http://127.0.0.1:9477/field | NEXUS C2 host desktop |
| http://127.0.0.1:9477/field-znetwork | ZNetwork Hub |
| http://127.0.0.1:9481/world/browser.html | Queen Browser (KILROY home) |
| http://127.0.0.1:9481/world/kilroy-home.html | KILROY homepage |
| http://127.0.0.1:9477/underlay-f9?sector=kilroy | KILROY tristate underlay |

## Install

```bash
git clone https://github.com/ZacharyGeurts/AmmoOS.git
cd AmmoOS
git checkout v2.0.0-beta3
./scripts/wire-stack.sh
sudo ./install-all.sh
```

Or extract release tarball:

```bash
tar -xzf ammooos-2.0.0-beta3-source.tar.gz
cd ammooos-2.0.0-beta3
sudo ./install-all.sh
```

## AmmoLang ship lane

```bash
./lib/ammolang-run.sh beta_pipeline
./lib/ammolang-run.sh github_mcp
./scripts/ammoos-release.sh --version 2.0.0-beta3 --push
./scripts/publish-stack-pages.sh
```

## Associated GitHub sites

| Repo | Pages | Wiki |
|------|-------|------|
| [AmmoOS](https://github.com/ZacharyGeurts/AmmoOS) | [Manual](https://zacharygeurts.github.io/AmmoOS/) | [Wiki](https://github.com/ZacharyGeurts/AmmoOS/wiki) |
| [Queen](https://github.com/ZacharyGeurts/Queen) | [Hub](https://zacharygeurts.github.io/Queen/) | — |
| [Grok16](https://github.com/ZacharyGeurts/Grok16) | [Manual](https://zacharygeurts.github.io/Grok16/) | [Wiki](https://github.com/ZacharyGeurts/Grok16/wiki) |
| [KILROY](https://github.com/ZacharyGeurts/KILROY) | [Manual](https://zacharygeurts.github.io/KILROY/) | [Wiki](https://github.com/ZacharyGeurts/KILROY/wiki) |
| [ZNetwork](https://github.com/ZacharyGeurts/ZNetwork) | [Manual](https://zacharygeurts.github.io/ZNetwork/) | [Wiki](https://github.com/ZacharyGeurts/ZNetwork/wiki) |
| [Stack hub](https://github.com/ZacharyGeurts/ZacharyGeurts) | [stack.html](https://zacharygeurts.github.io/ZacharyGeurts/stack.html) | — |

## Expert review

| Gate | Verdict |
|------|---------|
| AmmoLang router | PASS |
| GitHub MCP transport | PASS |
| KILROY legacy regression | PASS |
| Launch verify | PASS |
| MCP publish | PASS |