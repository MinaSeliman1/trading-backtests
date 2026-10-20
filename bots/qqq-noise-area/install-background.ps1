param([switch]$StartNow)
. (Join-Path $PSScriptRoot 'windows-common.ps1')
$qqqPythonw = Get-QqqPython -Windowless
$qqqBootstrap = Join-Path $PSScriptRoot 'scripts/background_bootstrap.py'
$qqqRuntime = Join-Path $PSScriptRoot 'runtime'
$qqqArguments = '"' + $qqqBootstrap + '" --runtime "' + $qqqRuntime + '"'
$qqqUser = [Security.Principal.WindowsIdentity]::GetCurrent()
$qqqExisting = Get-ScheduledTask -TaskName $qqqTaskName -ErrorAction SilentlyContinue
if ($qqqExisting -and ($qqqExisting.Actions.Arguments -notcontains $qqqArguments)) {
    throw 'The reserved task name already has another action; refusing to replace it.'
}
$qqqAction = New-ScheduledTaskAction -Execute $qqqPythonw -Argument $qqqArguments -WorkingDirectory $PSScriptRoot
$qqqTrigger = New-ScheduledTaskTrigger -AtLogOn -User $qqqUser.Name
$qqqTrigger.Delay = 'PT20S'
$qqqPrincipal = New-ScheduledTaskPrincipal -UserId $qqqUser.User.Value -LogonType Interactive -RunLevel Limited
$qqqSettings = New-ScheduledTaskSettingsSet -Hidden -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$qqqTask = New-ScheduledTask -Action $qqqAction -Trigger $qqqTrigger -Principal $qqqPrincipal -Settings $qqqSettings -Description 'QQQ Noise Area shadow SIP simulation only. No broker orders. Credentials in current-user Windows vault.'
Register-ScheduledTask -TaskName $qqqTaskName -InputObject $qqqTask -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $qqqRuntime 'windows') -Force | Out-Null
Export-ScheduledTask -TaskName $qqqTaskName | Set-Content -LiteralPath (Join-Path $qqqRuntime 'windows/task.xml') -Encoding UTF8
[ordered]@{ task_name=$qqqTaskName; trigger='Windows user logon, delay 20 seconds'; mode='shadow'; feed='sip'; executable='pythonw.exe'; utc=[DateTime]::UtcNow.ToString('o') } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $qqqRuntime 'windows/installation.json') -Encoding UTF8
Write-Output ('Installed automatic simulation task: ' + $qqqTaskName)
if ($StartNow) { & (Join-Path $PSScriptRoot 'start-background.ps1') }
