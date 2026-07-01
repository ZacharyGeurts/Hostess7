# secure_clipboard.ps1 — RAM-vault clipboard, auto-wipe, no Windows clipboard history/cloud
#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

$script:SClipCfgDir  = Join-Path $env:USERPROFILE '.config\secure-clipboard'
$script:SClipPassFile = Join-Path $script:SClipCfgDir 'passphrase.dpapi'
$script:SClipEnvFile  = Join-Path $script:SClipCfgDir 'env.ps1'
$script:SClipVaultDir = Join-Path $env:TEMP "sclip-$env:USERNAME"
$script:SClipVaultFile = Join-Path $script:SClipVaultDir 'vault.dat'
$script:SClipMetaFile  = Join-Path $script:SClipVaultDir 'meta.txt'
$script:SClipWatcher   = Join-Path $script:SClipVaultDir 'watcher.job'
$script:SClipTtlSec    = 45
$script:SClipVaultTtl  = 300

if (Test-Path $script:SClipEnvFile) { . $script:SClipEnvFile }

function Write-SClipLog([string]$Msg) { Write-Host "[sclip] $Msg" }

function Ensure-SClipDir {
    New-Item -ItemType Directory -Force -Path $script:SClipCfgDir | Out-Null
    New-Item -ItemType Directory -Force -Path $script:SClipVaultDir | Out-Null
}

function Get-SClipPassphrase {
    if (Test-Path $script:SClipPassFile) {
        $enc = Get-Content -Raw -Path $script:SClipPassFile
        $bytes = [Convert]::FromBase64String($enc.Trim())
        $plain = [Security.Cryptography.ProtectedData]::Unprotect(
            $bytes, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
        return [Text.Encoding]::UTF8.GetString($plain)
    }
    if ([Console]::IsInputRedirected -eq $false) {
        $s1 = Read-Host 'sclip vault passphrase' -AsSecureString
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s1)
        try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
        finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
    }
    throw 'No passphrase file. Run: .\amouranth.ps1 clip -Init'
}

function Save-SClipPassphrase([string]$Plain) {
    Ensure-SClipDir
    $bytes = [Text.Encoding]::UTF8.GetBytes($Plain)
    $prot = [Security.Cryptography.ProtectedData]::Protect(
        $bytes, $null, [Security.Cryptography.DataProtectionScope]::CurrentUser)
    [Convert]::ToBase64String($prot) | Set-Content -Path $script:SClipPassFile -NoNewline
    icacls $script:SClipPassFile /inheritance:r /grant:r "$env:USERNAME:(R)" | Out-Null
}

function Protect-Vault([string]$PlainText, [string]$Passphrase) {
    $salt = New-Object byte[] 16
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($salt)
    $derive = New-Object Security.Cryptography.Rfc2898DeriveBytes($Passphrase, $salt, 250000)
    $key = $derive.GetBytes(32)
    $aes = [Security.Cryptography.Aes]::Create()
    $aes.Key = $key
    $aes.GenerateIV()
    $enc = $aes.CreateEncryptor()
    $plainBytes = [Text.Encoding]::UTF8.GetBytes($PlainText)
    $cipher = $enc.TransformFinalBlock($plainBytes, 0, $plainBytes.Length)
    $payload = [byte[]]($salt + $aes.IV + $cipher)
    [IO.File]::WriteAllBytes($script:SClipVaultFile, $payload)
    [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() | Set-Content $script:SClipMetaFile
}

function Unprotect-Vault([string]$Passphrase) {
    if (-not (Test-Path $script:SClipVaultFile)) { throw 'vault empty' }
    $payload = [IO.File]::ReadAllBytes($script:SClipVaultFile)
    $salt = $payload[0..15]
    $iv   = $payload[16..31]
    $cipher = $payload[32..($payload.Length - 1)]
    $derive = New-Object Security.Cryptography.Rfc2898DeriveBytes($Passphrase, $salt, 250000)
    $key = $derive.GetBytes(32)
    $aes = [Security.Cryptography.Aes]::Create()
    $aes.Key = $key
    $aes.IV = $iv
    $dec = $aes.CreateDecryptor()
    $plain = $dec.TransformFinalBlock($cipher, 0, $cipher.Length)
    return [Text.Encoding]::UTF8.GetString($plain)
}

function Test-VaultExpired {
    if (-not (Test-Path $script:SClipMetaFile)) { return $true }
    $created = [int64](Get-Content $script:SClipMetaFile -Raw)
    $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    return (($now - $created) -gt $script:SClipVaultTtl)
}

function Stop-SClipWatcher {
    Get-Job -Name 'SClipWatcher' -ErrorAction SilentlyContinue | Stop-Job -PassThru |
        Remove-Job -Force -ErrorAction SilentlyContinue
}

function Start-SClipWatcher {
    Stop-SClipWatcher
    $sec = $script:SClipTtlSec
    Start-Job -Name 'SClipWatcher' -ScriptBlock {
        param($Seconds)
        Start-Sleep -Seconds $Seconds
        Set-Clipboard -Value ' ' -ErrorAction SilentlyContinue
        if (Get-Command Clear-Clipboard -ErrorAction SilentlyContinue) {
            Clear-Clipboard
        }
    } -ArgumentList $sec | Out-Null
}

function Disable-WindowsClipboardLeak {
    Write-SClipLog 'disable Windows clipboard history + cloud sync'
    $key = 'HKCU:\Software\Microsoft\Clipboard'
    if (-not (Test-Path $key)) { New-Item -Path $key -Force | Out-Null }
    Set-ItemProperty -Path $key -Name EnableClipboardHistory -Type DWord -Value 0 -Force
    Set-ItemProperty -Path $key -Name EnableCloudClipboard    -Type DWord -Value 0 -Force
    Stop-Process -Name 'ClipboardServer' -Force -ErrorAction SilentlyContinue
}

function Initialize-SecureClipboard {
    Ensure-SClipDir
    if (-not (Test-Path $script:SClipPassFile)) {
        $p1 = Read-Host 'Choose vault passphrase'
        $p2 = Read-Host 'Confirm passphrase'
        if ($p1 -ne $p2) { throw 'passphrases mismatch' }
        Save-SClipPassphrase $p1
        Write-SClipLog "passphrase saved (DPAPI): $script:SClipPassFile"
    }
    @"
`$script:SClipTtlSec = $script:SClipTtlSec
`$script:SClipVaultTtl = $script:SClipVaultTtl
"@ | Set-Content $script:SClipEnvFile
    Disable-WindowsClipboardLeak
    Write-SClipLog 'secure clipboard ready'
}

function Copy-SecureClipboard {
    param([Parameter(ValueFromPipeline)][string]$Text)
    Ensure-SClipDir
    if (-not $Text) {
        $Text = [Console]::In.ReadToEnd()
    }
    if ([string]::IsNullOrEmpty($Text)) { throw 'nothing to copy' }
    $pass = Get-SClipPassphrase
    Protect-Vault $Text $pass
    Set-Clipboard -Value $Text
    Start-SClipWatcher
    Write-SClipLog "copied — OS clipboard wipes in ${script:SClipTtlSec}s"
}

function Paste-SecureClipboard {
    if (Test-VaultExpired) { Clear-SecureClipboard; throw 'vault expired' }
    $pass = Get-SClipPassphrase
    Unprotect-Vault $pass
}

function Clear-SecureClipboard {
    Stop-SClipWatcher
    Remove-Item -Force -ErrorAction SilentlyContinue $script:SClipVaultFile, $script:SClipMetaFile
    Set-Clipboard -Value ' ' -ErrorAction SilentlyContinue
    if (Get-Command Clear-Clipboard -ErrorAction SilentlyContinue) { Clear-Clipboard }
    Write-SClipLog 'vault + clipboard cleared'
}

function Get-SecureClipboardStatus {
    Ensure-SClipDir
    [pscustomobject]@{
        VaultDir   = $script:SClipVaultDir
        TtlSec     = $script:SClipTtlSec
        VaultTtl   = $script:SClipVaultTtl
        VaultActive = (Test-Path $script:SClipVaultFile)
        VaultExpired = (Test-VaultExpired)
        Watcher    = [bool](Get-Job -Name 'SClipWatcher' -ErrorAction SilentlyContinue)
    }
}

# Aliases when dot-sourced
Set-Alias -Name scopy  -Value Copy-SecureClipboard  -Scope Global -ErrorAction SilentlyContinue
Set-Alias -Name spaste -Value Paste-SecureClipboard -Scope Global -ErrorAction SilentlyContinue
Set-Alias -Name sclear -Value Clear-SecureClipboard -Scope Global -ErrorAction SilentlyContinue