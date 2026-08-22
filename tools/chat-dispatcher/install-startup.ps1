param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot 'config.json')
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$dispatcher = Join-Path $PSScriptRoot 'dispatcher.ps1'
if (-not (Test-Path -LiteralPath $dispatcher)) {
    throw "dispatcher.ps1 not found: $dispatcher"
}
if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "config not found: $ConfigPath"
}

$startup = [Environment]::GetFolderPath('Startup')
$cmdPath = Join-Path $startup 'AgentChatDispatcher.cmd'
$escapedDispatcher = $dispatcher.Replace('"', '""')
$escapedConfig = (Resolve-Path -LiteralPath $ConfigPath).Path.Replace('"', '""')

$content = "@echo off`r`nstart \"\" powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Minimized -File \"$escapedDispatcher\" -ConfigPath \"$escapedConfig\"`r`n"
Set-Content -LiteralPath $cmdPath -Value $content -Encoding ASCII

Write-Host "Installed startup launcher: $cmdPath"
Write-Host "It will run at the next Windows sign-in."
Write-Host "To remove it, delete that .cmd file."
