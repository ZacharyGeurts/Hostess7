# Amouranth Shield v2 — Architecture & Design Document

**Glamorous defense, ruthless logic.**

| Field | Value |
|-------|-------|
| **Project** | Amouranth Shield (formerly AmmoSecurity) |
| **Main entry** | `ammo.sh` |
| **Branding** | Glamorous, sharp, no-nonsense terminal experience |
| **Version** | 2.0 |
| **Date** | June 22, 2026 |
| **Author** | Grok (xAI) — for ZacharyGeurts |

---

## 1. Vision & Goals

### Core vision

Turn a powerful collection of privacy and hardening scripts into a cohesive, menu-driven **desktop defense system** that feels premium in the terminal.

### Primary goals

- One-command or interactive control over network modes (WiFi / Ethernet / Both / Airgap) with hard kill-switch enforcement.
- Strong screen capture resistance while keeping full desktop visibility and **perfect OBS Studio compatibility** (PipeWire).
- Clean, pure-shell tick-box menu (56-column fixed borders, no zenity or GUI dependencies).
- Defense-in-depth with **mandatory core protections** plus **user-controlled toggles**.
- Excellent observability, reversibility, and legacy `-Action` compatibility.
- Professional enough to share with serious reviewers.

### Non-goals (v2)

- External GUI toolkits (zenity, whiptail forms, etc.).
- Requiring Wayland exclusively (support X11 gracefully where possible).
- Perfect protection against kernel rootkits or hardware implants.

---

## 2. Threat model

**Assumed adversaries**

- Malware / spyware attempting screen scraping or network exfiltration.
- Local attackers with user-level access.
- Remote attackers via compromised apps or unexpected interface activation.

**Key assets**

- Screen content (visual data).
- Network traffic (wrong interface egress, VPN drop leaks).
- Clipboard, processes, ingress vectors (USB/BT/WiFi hardware).

**Policy**

- **ClamAV removed** — purge on every scan; rkhunter, chkrootkit, heuristics retained.
- All other legacy modules retained (ingress clasp, FCC, dead-air, etc.).

---

## 3. High-level architecture

```
ammo.sh                          Main entry + command router
├── modules/ammo_gui.sh          Pure-shell tick-box menu (default)
├── lib/common.sh                Logging, sudo, nft, portal helpers
├── modules/
│   ├── net_mode.sh              WiFi / Ethernet / Both / Airgap
│   ├── interface_guard.sh       nftables kill-switch
│   ├── screen_guard.sh          Capture hardening + watch
│   ├── obs_compat.sh            OBS PipeWire whitelist
│   ├── ammo_watch.sh            30s re-enforcement timer
│   ├── net_harden.sh            Kernel, SMB, ufw/iptables
│   ├── ingress_clasp.sh         USB/BT/WiFi ingress lock
│   ├── antivirus.sh             rkhunter/chkrootkit (no ClamAV)
│   └── …                        surveillance, FCC, clipboard, etc.
└── state
    ├── ~/.config/ammo-shield/prefs     User toggles (WiFi, Eth, OBS, …)
    └── /var/lib/ammosecurity/          Runtime state + violations.log
```

**Wrappers:** `amouranth.sh`, `michigan.sh` → forward to `ammo.sh`.

### Key principles

| Layer | Behavior |
|-------|----------|
| **Mandatory core** | Always active — firewall, screen guard, watcher, ClamAV purge, surveillance, FCC, kill-switch logic |
| **User toggles** | Start OFF — WiFi, Ethernet, OBS, clipboard, ingress clasp unlock |
| **Fail-closed** | Airgap + drop policies when `--killswitch` is set |
| **Pure shell** | Maximum portability, minimal dependencies |

---

## 4. Tick-box menu system

First-class architectural component — not an afterthought.

### Layout

- Fixed **56-column** borders (`54` rule chars between corners; `52` inner text width).
- `[x]` / `[ ]` ticks for mandatory (always `[x]`) and user toggles.
- Keyboard-driven: `1`–`5` flip toggles; `a` apply; `t` test live; `s` status; `r` refresh mandatory; `0` quit.

### Persistence

```
~/.config/ammo-shield/prefs

WIFI=0
ETHERNET=0
OBS=0
CLIPBOARD=0
CLASP_UNLOCK=0
```

On every launch: mandatory baseline runs first, then saved ON ticks are restored. User can test an app, return to the menu — choices are remembered.

### Commands

```bash
./ammo.sh                  # menu (default)
./ammo.sh secure           # mandatory + restore ticks (login autostart)
./ammo.sh install-gui      # desktop launcher + autostart
```

---

## 5. Network isolation (WiFi / Ethernet / kill-switch)

### 5.1 Modes

| Mode | Behavior |
|------|----------|
| `wifi` | WiFi up; Ethernet down; rfkill managed |
| `ethernet` | Ethernet up; WiFi down + rfkill block |
| `both` | Dual-homed; still hardened via `net_harden.sh` |
| `airgap` | All external interfaces down; nft allows only `lo` |

Menu derives mode from toggles: both WiFi+Eth ON → `both`; one ON → that mode; neither → `airgap`.

### 5.2 Enforcement layers

1. **Interface layer** (`net_mode.sh`) — `nmcli`, `ip link`, `rfkill`
2. **Firewall layer** (`interface_guard.sh`) — dedicated nftables table
3. **Monitoring layer** (`ammo_watch.sh`) — systemd user timer re-applies mode + screen watch every 30s

### 5.3 nftables (`inet amouranth_shield`)

```nft
table inet amouranth_shield {
    set allowed_ifaces {
        type ifname
        elements = { "wlan0", "lo" }
    }
    chain input {
        type filter hook input priority filter; policy drop;
        iifname lo accept
        iifname @allowed_ifaces ct state established,related accept
        counter drop comment "Amouranth Shield input"
    }
    chain forward {
        type filter hook forward priority filter; policy drop;
    }
    chain output {
        type filter hook output priority filter; policy drop;
        oifname @allowed_ifaces accept
        ct state established,related accept
        counter drop comment "Amouranth Shield kill-switch"
    }
}
```

With `--killswitch`, output policy is `drop`. Without it, output policy is `accept` but allowed-interface set still applies.

Legacy table name `inet ammosecurity` is removed on apply for migration.

### 5.4 Commands

```bash
./ammo.sh net wifi --killswitch
./ammo.sh net ethernet
./ammo.sh net both
./ammo.sh net airgap
./ammo.sh net status
./ammo.sh watch on
```

**VPN-only (`--vpn-only` or menu toggle `6`):** egress restricted to `tun*` / `wg*` interfaces when active.

---

## 6. Screen capture hardening

### 6.1 Core approach (2026)

- **Wayland + PipeWire + xdg-desktop-portal** — primary secure path.
- Permissions are the main control point.
- Baseline: revoke capture for untrusted apps; whitelist OBS only.
- X11 fallback: kill/monitor `scrot`, `import`, `ffmpeg x11grab`, etc.

### 6.2 Layers

| Layer | Module | Role |
|-------|--------|------|
| Portal permissions | `screen_guard.sh` | Revoke Flatpak capture; OBS exception |
| Process watch | `screen_guard.sh` | Block rogue capture binaries |
| OBS setup | `obs_compat.sh` | Portal backends, env, Flatpak perms |

### 6.3 OBS compatibility

```bash
./ammo.sh obs
```

- Installs portal + PipeWire deps.
- Grants `com.obsproject.Studio` screen-capture (Flatpak).
- Native OBS: `QT_QPA_PLATFORM=wayland`, PipeWire source in OBS UI.

**Result:** Unauthorized apps denied or black capture. Desktop rendering untouched. OBS recording works normally.

### 6.4 Commands

```bash
./ammo.sh screen on
./ammo.sh screen off
./ammo.sh screen status
./ammo.sh obs
```

---

## 7. Integration & CLI reference

### Primary commands

```bash
./ammo.sh                  menu
./ammo.sh lock             full hardening one shot
./ammo.sh unlock           cool down
./ammo.sh status           dashboard
./ammo.sh scan             rkhunter/chkrootkit
./ammo.sh purge-clam       remove ClamAV only
./ammo.sh clasp unlock     release ingress
./ammo.sh clip             secure clipboard
```

### Legacy

```bash
./ammo.sh -Action HardAll    # → lock
./ammo.sh -Action NetMode wifi
./ammo.sh -Action ScreenHard enable
./ammo.sh -Action OBSSetup
```

### Module map

| Module | Purpose |
|--------|---------|
| `ammo_gui.sh` | Tick-box menu + prefs |
| `net_mode.sh` | Interface mode enforcement |
| `interface_guard.sh` | nftables kill-switch |
| `screen_guard.sh` | Capture hardening |
| `obs_compat.sh` | OBS whitelist |
| `ammo_watch.sh` | Background re-enforcement |
| `ingress_clasp.sh` | USB/BT/WiFi ingress lock |
| `secure_clipboard.sh` | RAM vault clipboard |

---

## 8. Security posture

### Strengths

- Multi-layer network control (interface + nft + watcher).
- Permission-based screen protection on modern desktops.
- Mandatory core always on; user only opts into exposure.
- Violations logged to `/var/lib/ammosecurity/violations.log`.
- Reversible: `./ammo.sh unlock`, toggle off, delete nft table.

### Trade-offs

- Portal setup required for best screen control (documented in `obs` helper).
- X11 is fundamentally leakier than Wayland.
- nftables misconfiguration can lock out network — use `status` and `unlock`.

### Mitigations

- `--killswitch` is explicit.
- Menu `t` key for live test before trusting a toggle.
- Prefs file is human-readable and editable.

---

## 9. Implementation status

| Component | Status |
|-----------|--------|
| `ammo.sh` command router | **Done** |
| `ammo_gui.sh` tick-box menu + prefs | **Done** |
| `net_mode.sh` | **Done** |
| `interface_guard.sh` | **Done** |
| `screen_guard.sh` | **Done** |
| `obs_compat.sh` | **Done** |
| `ammo_watch.sh` | **Done** |
| README + this design doc | **Done** |
| Multi-DE / OBS test matrix | Pending |
| VPN-only nft egress (`--vpn-only`) | **Done** |
| Dry-run nft preview (`net dry-run`) | **Done** |
| MAC randomize on WiFi | **Done** |
| Menu helpers in `common.sh` | **Done** |
| AppArmor capture profiles | Pending (v2.5) |

---

## 10. Roadmap

### v2.0 (current)

- [x] Amouranth Shield branding
- [x] Pure-shell menu with persisted toggles
- [x] Network modes + kill-switch
- [x] Screen guard + OBS compat
- [x] Watcher + violation logging
- [x] ClamAV purge policy

### v2.5+

- Grok/xAI-assisted anomaly alerts on violation log
- VPN-only egress in `interface_guard.sh`
- Hardware kill-switch integration where available
- Stronger sandboxing (AppArmor)
- Public release polish (LICENSE, media assets, CI shellcheck)

---

## 11. References

- PipeWire + xdg-desktop-portal (Wayland screen sharing)
- nftables kill-switch patterns (VPN-style)
- OBS Wayland/PipeWire requirements
- privsec.dev, Kicksecure hardening guides

---

*Amouranth Shield v2 — Grok (xAI), for ZacharyGeurts. June 2026.*