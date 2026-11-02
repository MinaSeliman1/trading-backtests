param([switch]$StartNow)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$taskName='TradingBacktests-QQQ-Simulation-Alerts'
$python='C:\Python314\pythonw.exe'
$worker=Join-Path $root 'scripts\watch.py'
if(!(Test-Path -LiteralPath $python) -or !(Test-Path -LiteralPath $worker)){throw 'Notification runtime unavailable.'}
if((Get-TimeZone).Id -ne 'Eastern Standard Time'){throw 'Eastern local time required; no timezone modified.'}
$old=Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if($old -and ($old.Actions.Execute -ne $python -or !$old.Actions.Arguments.Contains($worker))){throw 'Unrelated existing task: replacement refused.'}
if($worker.Contains('"')){throw 'Unexpected quoted worker path.'}
$action=New-ScheduledTaskAction -Execute $python -Argument ('"'+$worker+'"') -WorkingDirectory $root
$user=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$login=New-ScheduledTaskTrigger -AtLogOn -User $user
$login.Delay='PT10S'
$morning=New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At '09:05'
$retry=New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(2)) -RepetitionInterval ([TimeSpan]::FromHours(1))
$settings=New-ScheduledTaskSettingsSet -Hidden -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval ([TimeSpan]::FromMinutes(1)) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($login,$morning,$retry) -Settings $settings -Principal $principal -Description 'Read-only technical alerts for QQQ shadow simulations; ntfy only, no broker keys or orders' -Force | Out-Null
if($StartNow){Start-ScheduledTask -TaskName $taskName}
[pscustomobject]@{task=$taskName;hidden=$true;simulation_only=$true;original_trading_tasks_modified=$false} | ConvertTo-Json -Compress
