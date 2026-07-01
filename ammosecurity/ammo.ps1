# legacy wrapper → sg_build.ps1
param([string]$Action = 'Help')
$SgDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
& "$SgDir\sg_build.ps1" @PSBoundParameters