# NEXUS Field Windows installer — Start Menu shortcut
param(
    [switch]$Portable,
    [switch]$System,
    [string]$Root = ""
)

$ErrorActionPreference = 'Stop'
if (-not $Root) { $Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent }
$Root = (Resolve-Path $Root).Path
$PanelUrl = 'http://127.0.0.1:9477/field'

function New-NexusStartMenuShortcut {
    param([string]$TargetPath, [string]$Name = 'NEXUS Field')
    $programs = [Environment]::GetFolderPath('Programs')
    $lnk = Join-Path $programs "$Name.lnk"
    $wsh = New-Object -ComObject WScript.Shell
    $sc = $wsh.CreateShortcut($lnk)
    $sc.TargetPath = $TargetPath
    $sc.WorkingDirectory = $Root
    $sc.Description = 'NEXUS Field Command Center — ZNetwork + panel'
    $icon = Join-Path $Root 'panel\assets\nexus-tray-us-64.png'
    if (Test-Path $icon) { $sc.IconLocation = $icon }
    $sc.Save()
    Write-Host "Start menu: $lnk"
}

$cmd = Join-Path $Root 'install\windows\NEXUS-Field.cmd'
@(
    '@echo off',
    'set "ROOT=%~dp0..\.."',
    'cd /d "%ROOT%"',
    'where bash >nul 2>&1',
    'if %ERRORLEVEL%==0 (',
    "  start `"`" `"$PanelUrl`"",
    '  bash nexus-launch.sh',
    ') else (',
    "  start `"`" `"$PanelUrl`"",
    '  echo Install Git Bash or WSL, then re-run install.ps1',
    '  pause',
    ')'
) | Set-Content -Path $cmd -Encoding ASCII

$znRoot = Join-Path (Split-Path $Root -Parent) 'ZNetwork'
if ((Test-Path $znRoot) -and (Get-Command cmake -ErrorAction SilentlyContinue)) {
    Write-Host 'Building ZNetwork (Windows)…'
    Push-Location $znRoot
    cmake -B build -DCMAKE_BUILD_TYPE=Release 2>$null
    cmake --build build 2>$null
    Pop-Location
    if (Test-Path (Join-Path $znRoot 'build\znetwork.exe')) {
        $dest = Join-Path $Root 'bin'
        New-Item -ItemType Directory -Force -Path $dest | Out-Null
        Copy-Item (Join-Path $znRoot 'build\znetwork.exe') (Join-Path $dest 'znetwork.exe') -Force
        Write-Host "ZNetwork: $(Join-Path $dest 'znetwork.exe')"
    }
}

if ($System) {
    if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Host 'Full install needs administrator approval (once)...'
        Start-Process powershell.exe -Verb RunAs -ArgumentList "-ExecutionPolicy Bypass -File `"$PSCommandPath`" -System -Root `"$Root`""
        exit 0
    }
}

New-NexusStartMenuShortcut -TargetPath $cmd
Write-Host "PORTABLE_OK root=$Root"
Write-Host "Panel: $PanelUrl"