# AmmoOS 2.0.0-beta3 — CANVAS

**[→ GitHub: ZacharyGeurts/AmmoOS](https://github.com/ZacharyGeurts/AmmoOS)** · [Manual](https://zacharygeurts.github.io/AmmoOS/) · [Stack hub](https://zacharygeurts.github.io/ZacharyGeurts/stack.html) · [Release v2.0.0-beta3](https://github.com/ZacharyGeurts/AmmoOS/releases/tag/v2.0.0-beta3)

AmmoOS beta 3 ships the full **NewLatest** stack: KILROY-first Queen UX, AmmoLang sovereign build, secure GitHub MCP, and tied Pages + wikis across ZacharyGeurts repos.

## Stack (top → bottom)

```
Hardware
  → NEXUS C2 (:9477)
  → ZNetwork (sole internet pipe)
  → Queen CANVAS
  → Queen Browser (:9481)
  → AmmoOS inside Queen
```

## Tied GitHub sites

| Component | Repo | Pages |
|-----------|------|-------|
| **AmmoOS** | [AmmoOS](https://github.com/ZacharyGeurts/AmmoOS) | [Manual](https://zacharygeurts.github.io/AmmoOS/) |
| Queen | [Queen](https://github.com/ZacharyGeurts/Queen) | [Hub](https://zacharygeurts.github.io/Queen/) |
| Grok16 | [Grok16](https://github.com/ZacharyGeurts/Grok16) | [Manual](https://zacharygeurts.github.io/Grok16/) |
| KILROY | [KILROY](https://github.com/ZacharyGeurts/KILROY) | [Manual](https://zacharygeurts.github.io/KILROY/) |
| ZNetwork | [ZNetwork](https://github.com/ZacharyGeurts/ZNetwork) | [Manual](https://zacharygeurts.github.io/ZNetwork/) |
| Kill-Grok-Orphans | [Kill-Grok-Orphans](https://github.com/ZacharyGeurts/Kill-Grok-Orphans) | [Site](https://zacharygeurts.github.io/Kill-Grok-Orphans/) |

## AmmoLang

All field tasks run through AmmoLang:

```bash
./lib/ammolang-run.sh beta_pipeline
./lib/ammolang-run.sh github_mcp
```

GitHub transport defaults to **secure MCP** (`grok_com_github`), not raw TCP.

## Install

```bash
git clone https://github.com/ZacharyGeurts/AmmoOS.git
cd AmmoOS && git checkout v2.0.0-beta3
./scripts/wire-stack.sh && sudo ./install-all.sh
```

---

**[→ GitHub: ZacharyGeurts/AmmoOS](https://github.com/ZacharyGeurts/AmmoOS)**