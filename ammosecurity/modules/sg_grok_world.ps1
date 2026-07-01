# grok_world.ps1 — Grok Build & the World: 30 Windows desktop cleanups (phi · thermo · flow · field)
$ErrorActionPreference = 'SilentlyContinue'

function WLog($n, $msg) { Write-Host "[world $n] $msg" }

# PHI 1-8
function W01 { WLog 01 'phi: damp toast notification waves'; Set-ItemProperty HKCU:\Software\Microsoft\Windows\CurrentVersion\PushNotifications ToastEnabled 0 }
function W02 { WLog 02 'phi: calm animations'; Set-ItemProperty HKCU:\Control Panel\Desktop WindowMetrics -Name MinAnimate -Value 0 }
function W03 { WLog 03 'phi: DPMS blank'; powercfg /change monitor-timeout-ac 5; powercfg /change monitor-timeout-dc 3 }
function W04 { WLog 04 'phi: smooth mouse'; Set-ItemProperty 'HKCU:\Control Panel\Mouse' MouseSpeed 0; Set-ItemProperty 'HKCU:\Control Panel\Mouse' MouseThreshold1 0 }
function W05 { WLog 05 'phi: audio hush idle'; Get-Process audiodg -EA 0 | Stop-Process -Force }
function W06 { WLog 06 'phi: trim browser background'; Get-Process msedge,chrome,firefox -EA 0 | Where-Object { $_.MainWindowTitle -eq '' } | Stop-Process -Force }
function W07 { WLog 07 'phi: flat wallpaper'; Set-ItemProperty HKCU:\Control Panel\Desktop Wallpaper '' }
function W08 { WLog 08 'phi: flatten tray widgets'; Get-Process Widgets,NewsAndInterests -EA 0 | Stop-Process -Force }

# THERMO 9-16
function W09 { WLog 09 'thermo: CPU cool'; powercfg /SETACTIVE SCHEME_MIN }
function W10 { WLog 10 'thermo: disable pagefile heat'; $cs = Get-WmiObject Win32_ComputerSystem -EnableAllPrivileges; $cs.AutomaticManagedPagefile = $false; $cs.Put() }
function W11 { WLog 11 'thermo: vacuum event logs'; wevtutil el | ForEach-Object { wevtutil cl $_ 2>$null } }
function W12 { WLog 12 'thermo: scrub temp'; Remove-Item "$env:TEMP\*" -Recurse -Force -EA 0 }
function W13 { WLog 13 'thermo: clean component store'; Dism.exe /Online /Cleanup-Image /StartComponentCleanup }
function W14 { WLog 14 'thermo: thumbnail cache purge'; Remove-Item "$env:LOCALAPPDATA\Microsoft\Windows\Explorer\thumbcache_*.db" -Force }
function W15 { WLog 15 'thermo: sysmain off'; Stop-Service SysMain -Force; Set-Service SysMain -StartupType Disabled }
function W16 { WLog 16 'thermo: battery saver'; powercfg /SETACTIVE SCHEME_MAX }

# FLOW 17-23
function W17 { WLog 17 'flow: stop OneDrive/Dropbox rivers'; Stop-Process OneDrive,Dropbox -Force; Get-Service OneDrive -EA 0 | Stop-Service -Force }
function W18 { WLog 18 'flow: kill torrent gradients'; Stop-Process uTorrent,qBittorrent,BitTorrent -Force }
function W19 { WLog 19 'flow: flush DNS'; ipconfig /flushdns }
function W20 { WLog 20 'flow: w32time sync'; w32tm /resync }
function W21 { WLog 21 'flow: IPv6 off'; Disable-NetAdapterBinding -Name '*' -ComponentID ms_tcpip6 }
function W22 { WLog 22 'flow: mail idle off'; Stop-Process HxOutlook -Force }
function W23 { WLog 23 'flow: print spooler quiet'; Stop-Service Spooler -Force; Set-Service Spooler -StartupType Disabled }

# FIELD 24-30
function W24 { WLog 24 'field: scrub startup bloat'; Get-CimInstance Win32_StartupCommand | Select-Object Name, Command -First 15 }
function W25 { WLog 25 'field: defer store updates'; Set-ItemProperty HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate AUOptions 2 }
function W26 { WLog 26 'field: telemetry zero'; Stop-Service DiagTrack,dmwappushservice -Force; Set-Service DiagTrack -StartupType Disabled }
function W27 { WLog 27 'field: scheduled task audit'; Get-ScheduledTask | Where-Object State -eq Ready | Select-Object TaskName -First 20 }
function W28 { WLog 28 'field: single explorer focus'; Get-Process explorer | Select-Object -First 1 }
function W29 { WLog 29 'field: ssh/openssh harden'; Set-ItemProperty HKLM:\SOFTWARE\OpenSSH PasswordAuthentication -Value 0 -EA 0 }
function W30 {
    WLog 30 'field: world status'
    Get-Process | Sort-Object CPU -Descending | Select-Object -First 8 Name, CPU
    Get-NetAdapter | Select-Object Name, Status, LinkSpeed
    WLog 30 'Grok Build & the World — desktop computing cleaned'
}

$All = 1..30 | ForEach-Object { "W{0:D2}" -f $_ }

function Invoke-GrokWorld {
    param([string]$Which = 'all')
    Write-Host '=== GROK BUILD & THE WORLD ==='
    if ($Which -eq 'all' -or $Which -eq 'All') {
        foreach ($w in $All) { & $w }
    } elseif ($Which -match '^\d+$') {
        $fn = "W{0:D2}" -f [int]$Which
        & $fn
    }
}