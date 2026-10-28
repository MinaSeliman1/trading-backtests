# Short weekday AC wake: check the two fixed shadow tasks independently.
. (Join-Path $PSScriptRoot 'windows-common.ps1')
$qqqWakeFolder=Join-Path $PSScriptRoot 'runtime/windows'
New-Item -ItemType Directory -Path $qqqWakeFolder -Force | Out-Null
function Get-ShadowWakeResult($BotRoot,$TaskName,$ExpectedPython) {
    $result=[ordered]@{state='checking';task_name=$TaskName;mode='shadow';feed='sip'}
    try {
        if (Test-Path -LiteralPath (Join-Path $BotRoot 'runtime/STOP_SHADOW.flag')) {
            $result.state='operator_stop'
        } else {
            $task=Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
            if ($task.State -eq 'Disabled') {
                $result.state='operator_disabled'
            } else {
                $expectedArgs='"'+(Join-Path $BotRoot 'scripts/background_bootstrap.py')+'" --runtime "'+(Join-Path $BotRoot 'runtime')+'"'
                if (@($task.Actions).Count -ne 1 -or $task.Actions[0].Execute -ne $ExpectedPython -or $task.Actions[0].Arguments -ne $expectedArgs -or $task.Actions[0].WorkingDirectory -ne $BotRoot) {
                    throw 'Reserved shadow task action has changed; refusing to start it.'
                }
                if ($task.State -eq 'Running') {$result.state='already_running'}
                else {Start-ScheduledTask -TaskName $TaskName -ErrorAction Stop;$result.state='start_requested'}
            }
        }
    } catch {$result.state='error';$result.error_type=$_.Exception.GetType().Name}
    return $result
}
$noise=Get-ShadowWakeResult $PSScriptRoot $qqqTaskName (Get-QqqPython -Windowless)
$orbRoot=Join-Path (Split-Path $PSScriptRoot -Parent) 'qqq-orb'
$orb=[ordered]@{state='not_installed';mode='shadow';feed='sip'}
if (Test-Path -LiteralPath (Join-Path $orbRoot 'scripts/background_bootstrap.py')) {
    # Match the existing ORB installer, without executing its scripts or reading keys.
    $orbPython=Join-Path 'C:/Python314' 'pythonw.exe'
    if (-not (Test-Path -LiteralPath $orbPython)) {$orbPython=(Get-Command pythonw.exe -ErrorAction Stop).Source}
    $orb=Get-ShadowWakeResult $orbRoot 'TradingBacktests-QQQ-ORB-Simulation' $orbPython
}
$failed=$noise.state -eq 'error' -or $orb.state -eq 'error'
$qqqWakeState=[ordered]@{state=$(if($failed){'error'}else{$noise.state});mode='shadow';feed='sip';utc=[DateTime]::UtcNow.ToString('o');bots=[ordered]@{noise=$noise;orb=$orb}}
$qqqWakeState | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $qqqWakeFolder 'wake_status.json') -Encoding UTF8
if ($failed) {Write-Error 'Wake check failed; inspect per-bot status. No task was killed or operator stop overridden.';exit 1}
Write-Output $qqqWakeState.state
