param([switch]$StartNow)
$ErrorActionPreference='Stop'
$botRoot=$PSScriptRoot
$taskName='TradingBacktests-QQQ-EOD-Operational-Ledger'
$worker=Join-Path $botRoot 'scripts\operational_worker.py'
$python='C:\Python314\pythonw.exe'
$gh=(Get-Command gh -ErrorAction Stop).Source
if((Get-TimeZone).Id -ne 'Eastern Standard Time'){throw 'Eastern local time is required; timezone was not modified.'}
if(!(Test-Path -LiteralPath $python) -or !(Test-Path -LiteralPath $worker)){throw 'Collector dependencies unavailable.'}
$old=Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if($old -and ($old.Actions.Execute -ne $python -or !$old.Actions.Arguments.Contains($worker))){throw 'Existing unrelated task: replacement refused.'}
foreach($value in @($worker,$gh)){if($value.Contains('"')){throw 'Unexpected quoted executable path.'}}
$arguments='"'+$worker+'" --gh-executable "'+$gh+'"'
$action=New-ScheduledTaskAction -Execute $python -Argument $arguments -WorkingDirectory $botRoot
$evening=New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At '18:35'
$retry=New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At '19:35'
$user=[System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$login=New-ScheduledTaskTrigger -AtLogOn -User $user
$login.Delay='PT2M'
$settings=New-ScheduledTaskSettingsSet -Hidden -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::FromMinutes(15)) -RunOnlyIfNetworkAvailable -RestartCount 2 -RestartInterval ([TimeSpan]::FromMinutes(5))
$principal=New-ScheduledTaskPrincipal -UserId $user -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($evening,$retry,$login) -Settings $settings -Principal $principal -Description 'Read-only QQQ operational ledger collector; no Alpaca key or trading engine' -Force | Out-Null
if($StartNow){Start-ScheduledTask -TaskName $taskName}
[pscustomobject]@{task=$taskName;read_only_live=$true;hidden=$true;times='18:35,19:35 Eastern weekdays; logon+2m';original_trading_tasks_modified=$false} | ConvertTo-Json -Compress
