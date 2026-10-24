. (Join-Path $PSScriptRoot 'windows-common.ps1')
$orbStop=Join-Path $PSScriptRoot 'runtime/STOP_SHADOW.flag'
$orbTask=Get-ScheduledTask -TaskName $orbTaskName
if ($orbTask.State -eq 'Running' -and -not (Test-Path -LiteralPath $orbStop)) { Write-Output 'ORB task already running.'; return }
$orbDeadline=[DateTime]::UtcNow.AddSeconds(90)
while ($orbTask.State -eq 'Running') {
    if ([DateTime]::UtcNow -gt $orbDeadline) { throw 'Prior ORB instance still stopping; STOP retained.' }
    Start-Sleep -Seconds 1
    $orbTask=Get-ScheduledTask -TaskName $orbTaskName
}
if (Test-Path -LiteralPath $orbStop) { Remove-Item -LiteralPath $orbStop }
Enable-ScheduledTask -TaskName $orbTaskName | Out-Null
Start-ScheduledTask -TaskName $orbTaskName
Write-Output 'ORB start requested; check runtime/status.json for readiness.'
