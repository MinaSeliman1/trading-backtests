. (Join-Path $PSScriptRoot 'windows-common.ps1')
& (Get-QqqPython) -m qqq_paper.windows_setup --check-stored
if ($LASTEXITCODE -ne 0) { throw 'Configure Windows PAPER credentials first.' }
$qqqStop = Join-Path $PSScriptRoot 'runtime/STOP_SHADOW.flag'
$qqqDeadline = [DateTime]::UtcNow.AddSeconds(120)
$qqqTask = Get-ScheduledTask -TaskName $qqqTaskName
if ($qqqTask.State -eq 'Running' -and -not (Test-Path -LiteralPath $qqqStop)) {
    Write-Output 'Background simulation task is already running; inspect its status file.'
    return
}
while ($qqqTask.State -eq 'Running') {
    if ([DateTime]::UtcNow -gt $qqqDeadline) { throw 'Prior task has not stopped; STOP flag retained. Inspect its status before retrying.' }
    Start-Sleep -Seconds 1
    $qqqTask = Get-ScheduledTask -TaskName $qqqTaskName
}
if (Test-Path -LiteralPath $qqqStop) { Remove-Item -LiteralPath $qqqStop }
Enable-ScheduledTask -TaskName $qqqTaskName | Out-Null
$qqqRequested = [DateTime]::UtcNow
Start-ScheduledTask -TaskName $qqqTaskName
$qqqSupervisor = Join-Path $PSScriptRoot 'runtime/windows/status.json'
$qqqDeadline = [DateTime]::UtcNow.AddSeconds(90)
while ([DateTime]::UtcNow -lt $qqqDeadline) {
    if (Test-Path -LiteralPath $qqqSupervisor) {
        try {
            $qqqStatus = Get-Content -LiteralPath $qqqSupervisor -Raw | ConvertFrom-Json
            if ($qqqStatus.state -eq 'supervising_shadow' -and ([DateTimeOffset]::Parse($qqqStatus.utc).UtcDateTime -ge $qqqRequested) -and (Get-Process -Id $qqqStatus.pid -ErrorAction SilentlyContinue)) {
                Write-Output 'Hidden shadow SIP supervisor started. Inspect runtime/shadow-sip/status.json for engine readiness.'
                return
            }
        } catch { }
    }
    Start-Sleep -Seconds 1
}
throw 'Task start requested but no fresh supervisor confirmation. Inspect the task and runtime/windows logs.'
