param([switch]$DisableStartup)
. (Join-Path $PSScriptRoot 'windows-common.ps1')
New-Item -ItemType Directory -Path (Join-Path $PSScriptRoot 'runtime') -Force | Out-Null
Set-Content -LiteralPath (Join-Path $PSScriptRoot 'runtime/STOP_SHADOW.flag') -Value 'Stop local simulation; preserve ledger.' -Encoding UTF8
if ($DisableStartup) { Disable-ScheduledTask -TaskName $orbTaskName | Out-Null }
Write-Output 'ORB stop requested; no virtual close invented, ledger retained.'
