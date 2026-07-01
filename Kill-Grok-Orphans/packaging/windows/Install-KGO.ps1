# Kill Grok Orphans — Windows install (requires Administrator)
#Requires -RunAsAdministrator
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Ver = if (Test-Path "$Root\VERSION") { (Get-Content "$Root\VERSION" -Raw).Trim() } else { "unknown" }

Write-Host "Kill Grok Orphans v$Ver — installing…"

$InstallDir = "$env:ProgramFiles\Kill-Grok-Orphans"
$ConfigDir  = "$env:ProgramData\kgo"
New-Item -ItemType Directory -Force -Path $InstallDir, $ConfigDir | Out-Null

Copy-Item "$Root\python\kgo_watchdog.py" "$InstallDir\kgo-watchdog.py" -Force
Copy-Item "$Root\data\kgo-patterns.json" "$ConfigDir\kgo-patterns.json" -Force

$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py -3" } else { "python" }
Invoke-Expression "$py -m pip install psutil"

$action = New-ScheduledTaskAction `
    -Execute $py `
    -Argument "`"$InstallDir\kgo-watchdog.py`" -c `"$ConfigDir\kgo-patterns.json`" -f"
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName "KillGrokOrphans" -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName "KillGrokOrphans"

Write-Host ""
Write-Host "Installed. Task: Get-ScheduledTask KillGrokOrphans"
Write-Host "One-shot:  $py `"$InstallDir\kgo-watchdog.py`" --once --dry-run -c `"$ConfigDir\kgo-patterns.json`""