# AmmoOS 2.0.0-beta6 — CLASSIC_START

**Tag:** `v2.0.0-beta6` · **Repo:** [ZacharyGeurts/AmmoOS](https://github.com/ZacharyGeurts/AmmoOS) · **Manual:** [zacharygeurts.github.io/AmmoOS](https://zacharygeurts.github.io/AmmoOS/) · **Prior:** [v2.0.0-beta5](https://github.com/ZacharyGeurts/AmmoOS/releases/tag/v2.0.0-beta5)

## Beta 6 highlights

- **CLASSIC_START** — restored classic Start menu; F-key HUD hidden; botnet panel wired
- **Phased stack boot** — NEXUS C2 → KILROY → KILROY iPXE → AmmoOS desktop, then stop; Queen Browser is on-demand new window only
- **Field IRC chat** — standalone Chat Terminal on desktop + Start; Ironclad BSP rollout (100-server batches, verified online)
- **GitHub incorporate** — best of upstream (root-status, watch-dhcp, truth-dns, Big Grin assets, H7-Updater wiki); local canonical wins on stack/IRC/desktop
- **War posture** — battle stations no-limit; fleet protect 2500/2500 DNS/DHCP; grok-spawner kill lanes hardened
- **WATCHGUARD carry-forward** — component seal, H7 OCR lanes, brain guard, command deck from beta4 retained

## Install

```bash
git clone https://github.com/ZacharyGeurts/AmmoOS.git
cd AmmoOS
git checkout v2.0.0-beta6
./scripts/wire-stack.sh
sudo ./install-all.sh
```

Or from release assets (source `.h7e` may exceed GitHub 2GiB — use installers tar or clone):

```bash
curl -LO …/ammoos-2.0.0-beta6-installers.tar.gz
tar xzf ammoos-2.0.0-beta6-installers.tar.gz
cd ammoos-2.0.0-beta6-installers
sudo ./install-all.sh
```

## Ship lane

```bash
./scripts/ammoos-release.sh --version 2.0.0-beta6 --push
```

## Pairings

| Component | Version |
|-----------|---------|
| Grok16 | 5.2.0 |
| KILROY | 1.1.0 |
| Hostess 7 | supreme authority + component seal |