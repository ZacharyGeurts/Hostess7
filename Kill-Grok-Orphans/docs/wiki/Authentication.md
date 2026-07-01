# Authentication

Kill Grok Orphans **must authenticate as a privileged user** on each OS. Orphan processes are often reparented from user sessions; killing them requires crossing session boundaries.

## Why root / admin is required

When `grok-firmware-audit.sh` orphans reparent to PID 1, they may still run as your user — but only root (or SYSTEM) can reliably enumerate and terminate them across all sessions without race conditions.

## Per-OS auth model

### Linux

| Method | Use case |
|--------|----------|
| `sudo packaging/linux/install.sh` | One-time install |
| systemd `User=root` | Always-on daemon |
| polkit rule (`kgo-polkit.rules`) | Optional one-shot scan with sudo group auth |

### macOS

| Method | Use case |
|--------|----------|
| `sudo packaging/macos/install.sh` | Install launchd daemon as root |
| Touch ID / admin password | macOS prompts on `sudo` |

### Windows

| Method | Use case |
|--------|----------|
| Run PowerShell **as Administrator** | Install |
| Scheduled Task as **SYSTEM** | Always-on watchdog |
| UAC prompt | Standard Windows admin elevation |

## Dry-run without killing

Safe preview (still needs read access to process table):

```bash
sudo kgo --once --dry-run
```