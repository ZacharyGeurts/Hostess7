# Architecture

**v10.4.3** — Event-driven genius layer under `nexus-genius.service`.

![Architecture](https://raw.githubusercontent.com/ZacharyGeurts/NEXUS-Shield/main/docs/images/io-architecture.svg)

---

## Runtime stack

| Layer | Path | Role |
|-------|------|------|
| Panel HTTP | `lib/threat-panel-http.py` | Loopback C2 `:9477` |
| Daemon | `lib/nexus-daemon.sh` | Watchers + vigil loop |
| Boot impl | `lib/nexus-boot-impl.sh` | Reload tech each boot |
| State | `/var/lib/nexus-shield` | JSON/TSV publish |
| Perimeter | `lib/firewall-sentinel.sh` | nftables takeover |

---

## Core modules

| Module | File | Role |
|--------|------|------|
| Shadow Reality | `lib/shadow-reality.sh` | File integrity inotify |
| Entropy Oracle | `lib/entropy-oracle.sh` | Payload entropy scoring |
| Behavior Symphony | `lib/behavior-symphony.sh` | Process behavior loop |
| Eternal Vigil | `lib/eternal-vigil.sh` | Alert mode + maintenance |
| Privacy Guard | `lib/privacy-guard.sh` | Sensitive path watch |
| Connection Gatekeeper | `lib/connection-gatekeeper.py` | 10-axis flow scoring |
| Threat Panel | `lib/threat-panel.sh` | State publish |
| Hostess7 bridge | `lib/hostess7-bridge.sh` | Brain corroboration |

---

## Field stack (wired)

`scripts/wire-stack.sh` symlinks siblings: Grok16, KILROY, Final_Eye, ZNetwork, Hostess7, etc.

Sense package meld: `lib/field-sense-package-meld.py` — Eye · Ear · ZOCR · Redata · Hostess7.

---

## Stealth / CPU

`NEXUS_FIELD_MAX=1` — workstation profile (not 5% stealth cap). Thermal governor optional. Event-driven inotify reduces polling.

→ Module pages: [Shadow Reality](Shadow-Reality) · [Entropy Oracle](Entropy-Oracle) · [Behavior Symphony](Behavior-Symphony)