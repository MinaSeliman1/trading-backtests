# Dedicated short task: it can wake Windows even if the long-running bot task
# remained Running throughout hibernation. No credentials, API or ledger access.
. (Join-Path $PSScriptRoot 'windows-common.ps1')
$qqqWakeFolder = Join-Path $PSScriptRoot 'runtime/windows'
New-Item -ItemType Directory -Path $qqqWakeFolder -Force | Out-Null
$qqqWakeState = [ordered]@{ state='checking'; mode='shadow'; feed='sip'; utc=[DateTime]::UtcNow.ToString('o') }
try {
    if (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'runtime/STOP_SHADOW.flag')) {
        $qqqWakeState.state='operator_stop'
    } else {
        $qqqWakeTask=Get-ScheduledTask -TaskName $qqqTaskName -ErrorAction Stop
        if ($qqqWakeTask.State -eq 'Disabled') {
            $qqqWakeState.state='operator_disabled'
        } else {
            $qqqExpectedArgs='"'+(Join-Path $PSScriptRoot 'scripts/background_bootstrap.py')+'" --runtime "'+(Join-Path $PSScriptRoot 'runtime')+'"'
            if (@($qqqWakeTask.Actions).Count -ne 1 -or $qqqWakeTask.Actions[0].Execute -ne (Get-QqqPython -Windowless) -or $qqqWakeTask.Actions[0].Arguments -ne $qqqExpectedArgs) {
                throw 'Reserved simulation task action has changed; refusing to start it.'
            }
            if ($qqqWakeTask.State -eq 'Running') {
                $qqqWakeState.state='already_running'
            } else {
                Start-ScheduledTask -TaskName $qqqTaskName -ErrorAction Stop
                $qqqWakeState.state='start_requested'
            }
        }
    }
    $qqqWakeState | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $qqqWakeFolder 'wake_status.json') -Encoding UTF8
    Write-Output $qqqWakeState.state
} catch {
    $qqqWakeState.state='error'
    $qqqWakeState.error_type=$_.Exception.GetType().Name
    $qqqWakeState | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $qqqWakeFolder 'wake_status.json') -Encoding UTF8
    Write-Error 'Wake check failed; inspect the reserved simulation task. No trading action was requested.'
    exit 1
}
