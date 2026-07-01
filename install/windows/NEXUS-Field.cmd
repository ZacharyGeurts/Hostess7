@echo off
set "ROOT=%~dp0..\.."
cd /d "%ROOT%"
where bash >nul 2>&1
if %ERRORLEVEL%==0 (
  start "" "http://127.0.0.1:9477/field"
  bash nexus-launch.sh
) else (
  start "" "http://127.0.0.1:9477/field"
  echo Install Git Bash or WSL, then re-run install.ps1
  pause
)