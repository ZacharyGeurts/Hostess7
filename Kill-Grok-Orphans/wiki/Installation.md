# Installation

Kill Grok Orphans must run with **elevated privileges** on every OS so it can kill reparented orphan processes from any user session.

## Linux (recommended — native `kgo` binary)

```bash
# From release tarball
curl -fsSL https://github.com/ZacharyGeurts/Kill-Grok-Orphans/releases/latest/download/kgo-1.0.0-linux-x86_64.tar.gz | tar -xz
sudo packaging/linux/install.sh
```

This installs:

- `/usr/local/sbin/kgo` — native daemon (Grok16-built)
- `/etc/kgo/kgo-patterns.json` — pattern config
- `kgo.service` — systemd unit (enabled, restarted)

Verify:

```bash
systemctl status kgo
sudo kgo --once --dry-run
journalctl -u kgo -f
```

## macOS

```bash
git clone https://github.com/ZacharyGeurts/Kill-Grok-Orphans.git
cd Kill-Grok-Orphans
sudo packaging/macos/install.sh
```

Installs a **launchd** daemon at `com.grok.killorphans` running `kgo-watchdog` as root.

## Windows

Open **PowerShell as Administrator**:

```powershell
git clone https://github.com/ZacharyGeurts/Kill-Grok-Orphans.git
cd Kill-Grok-Orphans
.\packaging\windows\Install-KGO.ps1
```

Registers a **Scheduled Task** (`KillGrokOrphans`) running as `SYSTEM` at startup.

## Uninstall

| OS | Command |
|----|---------|
| Linux | `sudo systemctl disable --now kgo && sudo rm /etc/systemd/system/kgo.service /usr/local/sbin/kgo` |
| macOS | `sudo launchctl bootout system/com.grok.killorphans && sudo rm /Library/LaunchDaemons/com.grok.killorphans.plist` |
| Windows | `Unregister-ScheduledTask -TaskName KillGrokOrphans -Confirm:$false` |