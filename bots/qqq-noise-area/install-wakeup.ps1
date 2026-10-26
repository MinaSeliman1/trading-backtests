param([switch]$EnableAcWakeTimers)
. (Join-Path $PSScriptRoot 'windows-common.ps1')
if ((Get-TimeZone).Id -ne 'Eastern Standard Time') {
    throw 'This weekday09:10 installation requires the Toronto/New York Windows timezone; no changes made.'
}
$qqqWakeName=$qqqTaskName+'-Wakeup'
$qqqWakeScript=Join-Path $PSScriptRoot 'wake-before-session.ps1'
if (-not (Test-Path -LiteralPath $qqqWakeScript)) { throw 'Wake checker is missing.' }
$qqqWakeExe=Join-Path $env:SystemRoot 'System32/WindowsPowerShell/v1.0/powershell.exe'
$qqqWakeArgs='-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "'+$qqqWakeScript+'"'
$qqqWakeExisting=Get-ScheduledTask -TaskName $qqqWakeName -ErrorAction SilentlyContinue
if ($qqqWakeExisting -and (@($qqqWakeExisting.Actions).Count -ne 1 -or $qqqWakeExisting.Actions[0].Execute -ne $qqqWakeExe -or $qqqWakeExisting.Actions[0].Arguments -ne $qqqWakeArgs)) {
    throw 'Reserved wake task name has another action; refusing replacement.'
}
$qqqSchemeText=(& powercfg /getactivescheme | Out-String)
if ($LASTEXITCODE -ne 0) { throw 'Cannot read active power scheme.' }
$qqqScheme=[regex]::Match($qqqSchemeText,'[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}').Value
if (-not $qqqScheme) { throw 'Cannot identify active power scheme.' }
$qqqTimerText=(& powercfg /query $qqqScheme SUB_SLEEP RTCWAKE | Out-String)
if ($LASTEXITCODE -ne 0) { throw 'Cannot read wake timer policy.' }
$qqqIndices=[regex]::Matches($qqqTimerText,'0x([0-9a-fA-F]{8})')
if ($qqqIndices.Count -ne 2) { throw 'Cannot identify AC/DC wake timer policy.' }
$qqqBeforeAc=[Convert]::ToInt32($qqqIndices[0].Groups[1].Value,16)
$qqqBeforeDc=[Convert]::ToInt32($qqqIndices[1].Groups[1].Value,16)
if ($qqqBeforeAc -ne 1 -and -not $EnableAcWakeTimers) {
    throw 'Ordinary AC wake timers are disabled. Inspect and rerun with -EnableAcWakeTimers; battery settings remain unchanged.'
}
$qqqWakeFolder=Join-Path $PSScriptRoot 'runtime/windows'
New-Item -ItemType Directory -Path $qqqWakeFolder -Force | Out-Null
$qqqBackup=Join-Path $qqqWakeFolder 'wake_policy_before.json'
if (-not (Test-Path -LiteralPath $qqqBackup)) {
    [ordered]@{scheme=$qqqScheme;ac=$qqqBeforeAc;dc=$qqqBeforeDc;utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $qqqBackup -Encoding UTF8
}
$qqqWakeUser=[Security.Principal.WindowsIdentity]::GetCurrent()
$qqqWakeAction=New-ScheduledTaskAction -Execute $qqqWakeExe -Argument $qqqWakeArgs -WorkingDirectory $PSScriptRoot
$qqqWakeTrigger=New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At '09:10'
# No fixed UTC offset: Task Scheduler must follow local Eastern DST rules.
$qqqWakeTrigger.StartBoundary=[DateTime]::Parse($qqqWakeTrigger.StartBoundary).ToString('yyyy-MM-ddTHH:mm:ss')
$qqqWakePrincipal=New-ScheduledTaskPrincipal -UserId $qqqWakeUser.User.Value -LogonType Interactive -RunLevel Limited
# Default battery restrictions are retained: no AllowStartIfOnBatteries or DontStopIfGoingOnBatteries.
$qqqWakeSettings=New-ScheduledTaskSettingsSet -Hidden -WakeToRun -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
$qqqWakeTask=New-ScheduledTask -Action $qqqWakeAction -Trigger $qqqWakeTrigger -Principal $qqqWakePrincipal -Settings $qqqWakeSettings -Description 'Weekday09:10 Eastern AC wake and fixed QQQ shadow SIP task health check; no orders, credentials or ledger access.'
Register-ScheduledTask -TaskName $qqqWakeName -InputObject $qqqWakeTask -Force | Out-Null
if ($qqqBeforeAc -ne 1) {
    & powercfg /setacvalueindex $qqqScheme SUB_SLEEP RTCWAKE 1
    if ($LASTEXITCODE -ne 0) { throw 'Wake task registered but enabling AC wake timers failed; installation is incomplete.' }
    & powercfg /setactive $qqqScheme
    if ($LASTEXITCODE -ne 0) { throw 'Wake task registered but applying AC wake policy failed; installation is incomplete.' }
}
Export-ScheduledTask -TaskName $qqqWakeName | Set-Content -LiteralPath (Join-Path $qqqWakeFolder 'wake_task.xml') -Encoding UTF8
[ordered]@{task_name=$qqqWakeName;weekday_local_time='09:10';timezone='Eastern Standard Time';mode='shadow';feed='sip';wake_to_run=$true;ac_timer_requested=1;dc_timer_before=$qqqBeforeDc;utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $qqqWakeFolder 'wake_installation.json') -Encoding UTF8
Write-Output 'Installed weekday09:10 AC wake task; operator stops and battery policy preserved.'
