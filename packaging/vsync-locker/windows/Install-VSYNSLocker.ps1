# VSYNC-Locker Windows install — Python guard + scheduled task
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Prefix = if ($env:VSYNC_INSTALL_ROOT) { $env:VSYNC_INSTALL_ROOT } else { "$env:LOCALAPPDATA\VSYNC-Locker" }
New-Item -ItemType Directory -Force -Path "$Prefix\lib","$Prefix\data","$Prefix\panel","$Prefix\.nexus-state" | Out-Null
Copy-Item -Recurse -Force "$Here\lib\*" "$Prefix\lib\"
Copy-Item -Recurse -Force "$Here\data\*" "$Prefix\data\"
Copy-Item -Recurse -Force "$Here\panel\*" "$Prefix\panel\"
$env:NEXUS_INSTALL_ROOT = $Prefix
$env:NEXUS_STATE_DIR = "$Prefix\.nexus-state"
python "$Prefix\lib\field-vsync-locker.py" harden
python "$Prefix\lib\field-vsync-locker.py" launch
$action = New-ScheduledTaskAction -Execute "python" -Argument "`"$Prefix\lib\field-vsync-locker.py`" guard --quiet" -WorkingDirectory $Prefix
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "VSYNC-Locker" -Action $action -Trigger $trigger -Force | Out-Null
Write-Host "[vsync-locker] installed at $Prefix"