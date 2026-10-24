param([switch]$StartNow)
. (Join-Path $PSScriptRoot 'windows-common.ps1')
$orbArguments='"'+(Join-Path $PSScriptRoot 'scripts/background_bootstrap.py')+'" --runtime "'+(Join-Path $PSScriptRoot 'runtime')+'"'
$orbExisting=Get-ScheduledTask -TaskName $orbTaskName -ErrorAction SilentlyContinue
if ($orbExisting -and ($orbExisting.Actions.Arguments -notcontains $orbArguments)) { throw 'Reserved task name has another action; refusing replacement.' }
$orbUser=[Security.Principal.WindowsIdentity]::GetCurrent()
$orbAction=New-ScheduledTaskAction -Execute (Get-OrbPython -Windowless) -Argument $orbArguments -WorkingDirectory $PSScriptRoot
$orbTrigger=New-ScheduledTaskTrigger -AtLogOn -User $orbUser.Name
$orbTrigger.Delay='PT20S'
$orbPrincipal=New-ScheduledTaskPrincipal -UserId $orbUser.User.Value -LogonType Interactive -RunLevel Limited
$orbSettings=New-ScheduledTaskSettingsSet -Hidden -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$orbTask=New-ScheduledTask -Action $orbAction -Trigger $orbTrigger -Principal $orbPrincipal -Settings $orbSettings -Description 'QQQ ORB local shadow SIP delayed16min. Data GET only, no broker orders.'
Register-ScheduledTask -TaskName $orbTaskName -InputObject $orbTask -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $PSScriptRoot 'runtime') -Force | Out-Null
Export-ScheduledTask -TaskName $orbTaskName | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'runtime/task.xml') -Encoding UTF8
Write-Output 'ORB hidden simulation installed for current-user logon.'
if ($StartNow) { & (Join-Path $PSScriptRoot 'start-background.ps1') }
