# Start Kill Grok Orphans scheduled task (admin)
#Requires -RunAsAdministrator
Start-ScheduledTask -TaskName "KillGrokOrphans"
Write-Host "KillGrokOrphans task started."