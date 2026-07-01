# Amouranth Shield (`ammo.sh`)

**Glamorous defense, ruthless logic.** Run everything from the terminal:

```bash
./ammo.sh                  # tick-box menu (default)
./ammo.sh lock             # one-shot full hardening
./ammo.sh status
```

## Tick-box menu

Pure shell. Fixed 56-column borders. No zenity.

- **Mandatory** (always on): firewall, screen guard, watcher, ClamAV purge, surveillance, FCC, kill-switch
- **Your toggles** (start OFF): WiFi, Ethernet, OBS, clipboard, ingress, VPN-only — press `1`–`6` to flip
- **`t`** test live, then come back — ON choices saved in `~/.config/ammo-shield/prefs`

```
╔══════════════════════════════════════════════════════╗
║              AMOURANTH SHIELD                        ║
║         glamorous defense, ruthless logic            ║
╚══════════════════════════════════════════════════════╝
```

## Commands

| Command | Action |
|---------|--------|
| `./ammo.sh` | Menu with `[x]` ticks |
| `./ammo.sh secure` | Mandatory + restore saved ticks (login autostart) |
| `./ammo.sh install-gui` | Desktop launcher + autostart |
| `./ammo.sh net wifi` | Network mode (`--killswitch` `--vpn-only`) |
| `./ammo.sh net dry-run wifi` | Preview nft rules, no apply |
| `./ammo.sh screen on` | Screen guard |
| `./ammo.sh obs` | OBS PipeWire |
| `./ammo.sh scan` | rkhunter/chkrootkit (no ClamAV) |

`amouranth.sh` and `michigan.sh` forward to `ammo.sh`. Legacy `-Action` still works.

## Design

Full architecture, threat model, nftables rules, and roadmap:

**[AMMOSECURITY_V2_DESIGN.md](./AMMOSECURITY_V2_DESIGN.md)**

| | |
|--|--|
| Entry | `ammo.sh` |
| Prefs | `~/.config/ammo-shield/prefs` |
| nft table | `inet amouranth_shield` |
| Legacy | `-Action`, `amouranth.sh`, `michigan.sh` |