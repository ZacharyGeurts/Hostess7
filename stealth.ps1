# NEXUS-Shield Windows — invisible background protection
#Requires -RunAsAdministrator
$ErrorActionPreference = 'SilentlyContinue'

$NexusRoot = Join-Path $env:ProgramData 'NEXUS'
$ShadowDir = Join-Path $NexusRoot 'shadow'
$AlertLog = Join-Path $NexusRoot 'nexus-alerts.log'
$WatchScript = Join-Path $NexusRoot 'nexus-watch.ps1'

New-Item -ItemType Directory -Force -Path $NexusRoot, $ShadowDir | Out-Null
if (-not (Test-Path $AlertLog)) { New-Item -ItemType File -Path $AlertLog -Force | Out-Null }

@'
$ErrorActionPreference = "SilentlyContinue"
$NexusRoot = "NEXUS_ROOT_PLACEHOLDER"
$ShadowDir = Join-Path $NexusRoot "shadow"
$AlertLog = Join-Path $NexusRoot "nexus-alerts.log"

function Write-NexusAlert($Module, $Message) {
    $line = "{0} [ALERT] {1}: {2}" -f (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"), $Module, $Message
    Add-Content -Path $AlertLog -Value $line
}

function Get-ShannonEntropy($Path) {
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -gt 65536) { $bytes = $bytes[0..65535] }
    if ($bytes.Length -eq 0) { return 0 }
    $freq = @{}
    foreach ($b in $bytes) { if ($freq.ContainsKey($b)) { $freq[$b]++ } else { $freq[$b] = 1 } }
    $entropy = 0.0
    foreach ($count in $freq.Values) { $p = $count / $bytes.Length; $entropy -= $p * [Math]::Log($p, 2) }
    return [Math]::Round($entropy, 4)
}

function Initialize-ShadowBaseline {
    $targets = @(
        "$env:WINDIR\System32\drivers\etc\hosts",
        "$env:USERPROFILE\.ssh\authorized_keys"
    )
    foreach ($t in $targets) {
        if (Test-Path $t) {
            $hash = (Get-FileHash $t -Algorithm SHA256).Hash
            $name = ($t -replace "[\\/:*?`"<>|]", "_")
            Set-Content (Join-Path $ShadowDir "$name.sha") $hash
        }
    }
}

Initialize-ShadowBaseline

while ($true) {
    Get-ChildItem $ShadowDir -Filter "*.sha" -ErrorAction SilentlyContinue | ForEach-Object {
        $stored = (Get-Content $_.FullName -Raw).Trim()
        $path = ($_.BaseName -replace "_", "\")
        if (Test-Path $path) {
            $current = (Get-FileHash $path -Algorithm SHA256).Hash
            if ($current -ne $stored) {
                Write-NexusAlert "shadow-reality" "SHADOW_REALITY_ALERT path=$path"
                Set-Content $_.FullName $current
            }
        }
    }

    Get-Process -ErrorAction SilentlyContinue | ForEach-Object {
        $score = 0
        if ($_.Path -match "\\Temp\\|\\AppData\\Local\\Temp\\") { $score += 20 }
        if ($_.ProcessName -match "wscript|cscript|mshta") { $score += 40 }
        if ($score -ge 50) {
            Write-NexusAlert "behavior-symphony" "BEHAVIOR_SYMPHONY_ALERT pid=$($_.Id) score=$score exe=$($_.Path)"
        }
    }

    $dirs = @([Environment]::GetFolderPath("Desktop"), "$env:USERPROFILE\Downloads")
    foreach ($dir in $dirs) {
        if (-not (Test-Path $dir)) { continue }
        Get-ChildItem $dir -File -ErrorAction SilentlyContinue | Select-Object -First 30 | ForEach-Object {
            if ($_.Extension -match "\.(zip|jpg|png|mp4|exe|dll)$") { return }
            $entropy = Get-ShannonEntropy $_.FullName
            if ($entropy -ge 7.2) {
                Write-NexusAlert "entropy-oracle" "ENTROPY_ORACLE_ALERT path=$($_.FullName) entropy=$entropy"
            }
        }
    }

    if (Test-Path "$env:USERPROFILE\.ssh\authorized_keys") {
        Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Id -gt 4 -and $_.ProcessName -match "powershell|cmd" } | ForEach-Object {
            Write-NexusAlert "privacy-guard" "PRIVACY_GUARD_ALERT pid=$($_.Id) comm=$($_.ProcessName) sensitive=authorized_keys"
        }
    }

    Start-Sleep -Seconds 300
}
'@ -replace 'NEXUS_ROOT_PLACEHOLDER', $NexusRoot | Set-Content -Path $WatchScript -Encoding UTF8

$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$WatchScript`""
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName 'NEXUS-Shield' -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force | Out-Null
Start-ScheduledTask -TaskName 'NEXUS-Shield'

# Disable local file sharing and network discovery (SMB, LLMNR broadcast surface)
Stop-Service -Name LanmanServer -Force -ErrorAction SilentlyContinue
Set-Service -Name LanmanServer -StartupType Disabled -ErrorAction SilentlyContinue
Get-NetFirewallRule -DisplayGroup 'File and Printer Sharing' -ErrorAction SilentlyContinue | Disable-NetFirewallRule -ErrorAction SilentlyContinue
Get-NetFirewallRule -DisplayGroup 'Network Discovery' -ErrorAction SilentlyContinue | Disable-NetFirewallRule -ErrorAction SilentlyContinue
Set-SmbServerConfiguration -EnableSMB1Protocol $false -Force -ErrorAction SilentlyContinue
Set-SmbServerConfiguration -EnableSMB2Protocol $false -Force -ErrorAction SilentlyContinue

exit 0