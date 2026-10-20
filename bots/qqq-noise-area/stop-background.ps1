param([switch]$DisableStartup)
. (Join-Path $PSScriptRoot 'windows-common.ps1')
$qqqStop = Join-Path $PSScriptRoot 'runtime/STOP_SHADOW.flag'
New-Item -ItemType Directory -Path (Split-Path -Parent $qqqStop) -Force | Out-Null
Set-Content -LiteralPath $qqqStop -Value 'Operator requested shadow stop; no broker orders.' -Encoding UTF8
if ($DisableStartup) { Disable-ScheduledTask -TaskName $qqqTaskName | Out-Null }
Write-Output 'Shadow stop requested; inspect runtime/windows/status.json for completion. Use start-background.ps1 to resume.'
