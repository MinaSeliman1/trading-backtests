from pathlib import Path
import os
import shutil
import subprocess
import pytest

BOT=Path(__file__).resolve().parents[1]


@pytest.mark.skipif(os.name!='nt',reason='PowerShell script contract')
@pytest.mark.parametrize('stopping',[False,True])
def test_start_waits_for_shutdown_but_does_not_duplicate_running_task(tmp_path,stopping):
    shutil.copyfile(BOT/'start-background.ps1',tmp_path/'start-background.ps1')
    (tmp_path/'windows-common.ps1').write_text("""
$ErrorActionPreference='Stop'
$qqqTaskName='TEST-ONLY'
function Get-QqqPython { Join-Path $PSScriptRoot 'fake-python.ps1' }
""",encoding='utf-8-sig')
    (tmp_path/'fake-python.ps1').write_text('$global:LASTEXITCODE=0',encoding='utf-8-sig')
    (tmp_path/'runtime/windows').mkdir(parents=True)
    if stopping:(tmp_path/'runtime/STOP_SHADOW.flag').touch()
    (tmp_path/'exercise.ps1').write_text("""
$global:qqqTestReads=0; $global:qqqTestStarted=0
function Get-ScheduledTask {
    $global:qqqTestReads++
    if ($global:qqqTestReads -le 2) { [pscustomobject]@{State='Running'} }
    elseif (-not $global:qqqTestStarted) { [pscustomobject]@{State='Ready'} }
    else { [pscustomobject]@{State='Running'} }
}
function Start-Sleep {}
function Enable-ScheduledTask {}
function Start-ScheduledTask {
    if ($global:qqqTestReads -le 2) { throw 'start lost while prior task exits' }
    if (Test-Path (Join-Path $PSScriptRoot 'runtime/STOP_SHADOW.flag')) { throw 'stop flag still present' }
    $global:qqqTestStarted++
    @{state='supervising_shadow';pid=$PID;utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content (Join-Path $PSScriptRoot 'runtime/windows/status.json')
}
& (Join-Path $PSScriptRoot 'start-background.ps1')
if (Test-Path (Join-Path $PSScriptRoot 'runtime/STOP_SHADOW.flag')) { throw 'stop flag not cleared' }
Write-Output ('started=' + $global:qqqTestStarted)
""",encoding='utf-8-sig')
    result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(tmp_path/'exercise.ps1')],capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stdout+result.stderr
    assert ('started=1' if stopping else 'started=0') in result.stdout
