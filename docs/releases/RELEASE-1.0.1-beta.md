# AmmoOS 1.0.1-beta

**Tag:** `v1.0.1-beta` · **Lineage:** NEXUS-Shield 10.4.1 · **Grok16:** 4.7.1 · **Platforms:** 10

## Patch (2026-06-27)

- **Grok16 4.7.1 pairing** — combinatronic + plate meld aligned with latest bench refresh
- **Field stack** — `TDIR`, `NEXUS_ZNETWORK=0`, boot-impl fast path for reliable panel bind
- **Docs + Pages** — manual and GitHub release assets refreshed

## Surfaces

| URL | Role |
|-----|------|
| http://127.0.0.1:9477/field | Host desktop |
| http://127.0.0.1:9477/command | Field C2 |
| http://127.0.0.1:9481/world/browser.html | Queen Browser |
| http://127.0.0.1:9477/underlay-f9?sector=underlay | Underlay F9 |

```bash
./scripts/ammoos-release.sh --version 1.0.1-beta --push
./scripts/publish-ammoos-pages.sh --version 1.0.1-beta
```
