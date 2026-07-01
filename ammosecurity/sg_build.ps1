# sg_build.ps1 — internet + no bullshit. SG firmware layer.
#Requires -RunAsAdministrator
param(
    [ValidateSet('All','Firmware','Internet','Clean','Net','TrustNobody','Antivirus','Status','Help')]
    [string]$Action = 'Help'
)

$Version = 9
$SgRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }

function Log($m) { Write-Host "[sg_build v$Version] $m" }

function Show-Help {
@"
sg_build.ps1 v$Version — internet + no bullshit

  .\sg_build.ps1 -Action All
  .\sg_build.ps1 -Action Firmware
  .\sg_build.ps1 -Action Internet
  .\sg_build.ps1 -Action Clean
  .\sg_build.ps1 -Action Status
"@
}

switch ($Action) {
    { $_ -in 'All','Firmware','TrustNobody','Antivirus' } {
        . "$SgRoot\modules\sg_firmware.ps1"
        Invoke-SGFirmware
        . "$SgRoot\modules\sg_grok_world.ps1"
        Invoke-GrokWorld 'all'
    }
    { $_ -in 'Internet','Net' } {
        . "$SgRoot\modules\sg_firmware.ps1"
        Internet-Only
        Log 'outbound internet policy set'
    }
    'Clean' {
        . "$SgRoot\modules\sg_grok_world.ps1"
        Invoke-GrokWorld 'all'
    }
    'Status' {
        Get-NetAdapter | Where-Object Status -eq 'Up' | Select-Object Name, LinkSpeed
        Get-Process | Sort-Object CPU -Descending | Select-Object -First 6 Name, CPU
    }
    default { Show-Help }
}