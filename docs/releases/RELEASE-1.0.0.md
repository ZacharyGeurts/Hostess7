# AmmoOS 1.0.0

**Tag:** `v1.0.0` · **Edition:** stable · **Lineage:** NEXUS-Shield 10.4.1 · **Grok16:** 4.7.1 · **Platforms:** 10

## What ships

- **AmmoOS 1.0.0 stable** — Queen underlying browser on `127.0.0.1`, ZNetwork 100% internet pipe
- **Local Truth DNS** — `lib/field-dns.py` loopback resolver; graceful takeover via `dns-service-takeover.py`
- **Local Field DHCP** — `lib/field-dhcp.py` LAN leases; DNS option 6 → `127.0.0.1`
- **Auto-connect** — `lib/field-local-dns-connect.py` steers resolv + DHCP client when our servers start
- **Doctrine-locked settings** — always optimal posture; operator comfort scale only
- **Combinatronic optimal pipeline** — rebalance, condense, combine, connect before pack

## Install (Linux x86_64)

```bash
tar -xzf ammoos-1.0.0-source.tar.gz
cd ammoos-1.0.0
sudo ./install-all.sh
```

## Surfaces

| URL | Role |
|-----|------|
| http://127.0.0.1:9477/field | Host desktop — first page |
| http://127.0.0.1:9477/command | Field C2 command deck |
| http://127.0.0.1:9481/world/browser.html | Queen Browser OS shell |
| http://127.0.0.1:9477/underlay-f9?sector=underlay | Underlay F9 Tristate |

## Local DNS/DHCP

| Service | Module | Connect |
|---------|--------|---------|
| Truth DNS | `lib/field-dns.py` | `127.0.0.1:53` loopback |
| Field DHCP | `lib/field-dhcp.py` | LAN pool when port 67 vacant |
| Auto-connect | `lib/field-local-dns-connect.py` | Steers when either starts |

Boot: `./nexus.sh` or `./scripts/ammoos-direct-start.sh` starts services and connect loop.

## Release pipeline

```bash
./scripts/ammoos-beta-pipeline.sh
./scripts/ammoos-launch-verify.sh
./scripts/pack-ammoos-release.sh --version 1.0.0
```

## Gates

1. Combinatronic optimal cycle writes `.nexus-state/ammoos-combinatronic-optimal.json`
2. Launch verify passes browser + program registry + sovereignty + local DNS/DHCP
3. Sovereignty posture reports 100% ZNetwork pipe on `127.0.0.1`
4. Platform manifest lists 10 target families
5. Local DNS/DHCP connect module present and wired at boot