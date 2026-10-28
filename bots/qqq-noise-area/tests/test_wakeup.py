"""Exercise PowerShell wake scripts only with fake scheduler/power commands."""
import json,os,shutil,subprocess
from pathlib import Path
import pytest
BOT=Path(__file__).resolve().parents[1]

@pytest.mark.skipif(os.name!='nt',reason='Windows wake task')
@pytest.mark.parametrize('case,expected,starts',[
    ('running','already_running',0),('ready','start_requested',1),('disabled','operator_disabled',0),
    ('stop','operator_stop',0),('foreign','error',0),('foreign_args','error',0)])
def test_checker_respects_operator_and_starts_only_reserved_shadow_task(tmp_path,case,expected,starts):
    shutil.copyfile(BOT/'wake-before-session.ps1',tmp_path/'wake-before-session.ps1')
    (tmp_path/'windows-common.ps1').write_text("""
$ErrorActionPreference='Stop'
$qqqTaskName='TEST-ONLY'
function Get-QqqPython { 'C:\\fake\\pythonw.exe' }
""",encoding='utf-8-sig')
    (tmp_path/'runtime/windows').mkdir(parents=True)
    if case=='stop':(tmp_path/'runtime/STOP_SHADOW.flag').touch()
    (tmp_path/'exercise.ps1').write_text("""
$global:started=0
function Get-ScheduledTask {
    $state=if ('CASE' -eq 'disabled') {'Disabled'} elseif ('CASE' -eq 'running') {'Running'} else {'Ready'}
    $exe=if ('CASE' -eq 'foreign') {'C:\\fake\\foreign.exe'} else {'C:\\fake\\pythonw.exe'}
    $arg='"'+(Join-Path $PSScriptRoot 'scripts/background_bootstrap.py')+'" --runtime "'+(Join-Path $PSScriptRoot 'runtime')+'"'
    if ('CASE' -eq 'foreign_args') {$arg+=' --mode paper'}
    [pscustomobject]@{State=$state;Actions=@([pscustomobject]@{Execute=$exe;Arguments=$arg;WorkingDirectory=$PSScriptRoot})}
}
function Start-ScheduledTask {$global:started++;Set-Content (Join-Path $PSScriptRoot 'start_count.txt') $global:started}
function Enable-ScheduledTask {throw 'must never override disabled task'}
& (Join-Path $PSScriptRoot 'wake-before-session.ps1')
Write-Output ('starts='+$global:started)
""".replace('CASE',case),encoding='utf-8-sig')
    p=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(tmp_path/'exercise.ps1')],capture_output=True,text=True,timeout=20)
    status=json.loads((tmp_path/'runtime/windows/wake_status.json').read_text(encoding='utf-8-sig'))
    assert status['state']==expected,(p.stdout,p.stderr,status)
    count_file=tmp_path/'start_count.txt'
    assert (int(count_file.read_text(encoding='utf-8-sig').strip()) if count_file.exists() else 0)==starts
    if expected!='error':assert p.returncode==0 and f'starts={starts}' in p.stdout
    assert status['mode']=='shadow' and status['feed']=='sip'
    assert not list(tmp_path.rglob('*.sqlite'))
    assert (tmp_path/'runtime/STOP_SHADOW.flag').exists()==(case=='stop')

@pytest.mark.skipif(os.name!='nt',reason='Windows task construction')
@pytest.mark.parametrize('boundary',['2026-10-26T09:10:00-04:00','2026-11-02T09:10:00-05:00'])
def test_installer_builds_separate_ac_only_weekday_wake_task_and_preserves_dc(tmp_path,boundary):
    shutil.copyfile(BOT/'install-wakeup.ps1',tmp_path/'install-wakeup.ps1')
    (tmp_path/'windows-common.ps1').write_text("""
$ErrorActionPreference='Stop'
$qqqTaskName='TEST-ONLY'
""",encoding='utf-8-sig')
    (tmp_path/'wake-before-session.ps1').write_text('# test',encoding='utf-8-sig')
    (tmp_path/'exercise.ps1').write_text("""
$global:powerCalls=@();$global:registered=$false
function powercfg {
 $global:powerCalls+=,($args -join ' ');$global:LASTEXITCODE=0
 if ($args[0] -eq '/getactivescheme') {'GUID: 381b4222-f694-41f0-9685-ff5bb260df2e'}
 elseif ($args[0] -eq '/query') {"AC Index: 0x00000002`nDC Index: 0x00000000"}
}
function Get-ScheduledTask {if ($TaskName -eq 'never') {throw 'unused'};return $null}
function New-ScheduledTaskAction {param($Execute,$Argument,$WorkingDirectory);[pscustomobject]@{Execute=$Execute;Arguments=$Argument}}
function New-ScheduledTaskTrigger {param([switch]$Weekly,$DaysOfWeek,$At);if(-not $Weekly -or $DaysOfWeek.Count -ne 5 -or $At -ne '09:10') {throw 'wrong weekday schedule'};[pscustomobject]@{At=$At;StartBoundary='BOUNDARY'}}
function New-ScheduledTaskPrincipal {param($UserId,$LogonType,$RunLevel);if($LogonType -ne 'Interactive' -or $RunLevel -ne 'Limited'){throw 'wrong principal'}}
function New-ScheduledTaskSettingsSet {param([switch]$Hidden,[switch]$WakeToRun,[switch]$StartWhenAvailable,$MultipleInstances,$ExecutionTimeLimit);if(-not($Hidden -and $WakeToRun -and $StartWhenAvailable)){throw 'wake flags missing'}}
function New-ScheduledTask {param($Action,$Trigger,$Principal,$Settings,$Description);if($Trigger.StartBoundary -notmatch '^[0-9]{4}-[0-9]{2}-[0-9]{2}T09:10:00$'){throw 'fixed offset would shift local wake after DST'};[pscustomobject]@{Description=$Description}}
function Register-ScheduledTask {param($TaskName,$InputObject,[switch]$Force);if($TaskName -ne 'TEST-ONLY-Wakeup'){throw 'wrong task name'};$global:registered=$true}
function Export-ScheduledTask {'<wake-test />'}
& (Join-Path $PSScriptRoot 'install-wakeup.ps1') -EnableAcWakeTimers
if(-not $global:registered){throw 'no registered wake task'}
if($global:powerCalls -match '/setdcvalueindex'){throw 'battery policy altered'}
if(-not ($global:powerCalls -match '/setacvalueindex .* SUB_SLEEP RTCWAKE 1')){throw 'AC timer not enabled'}
Write-Output 'installer-contract-pass'
""".replace('BOUNDARY',boundary),encoding='utf-8-sig')
    p=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(tmp_path/'exercise.ps1')],capture_output=True,text=True,timeout=20)
    assert p.returncode==0 and 'installer-contract-pass' in p.stdout,p.stdout+p.stderr


@pytest.mark.skipif(os.name!='nt',reason='Windows wake checker')
@pytest.mark.parametrize('case,noise_state,orb_state,count',[
    ('both_running','already_running','already_running',0),
    ('orb_ready','already_running','start_requested',1),
    ('both_ready','start_requested','start_requested',2),
    ('orb_stop','already_running','operator_stop',0),
    ('orb_disabled','already_running','operator_disabled',0),
    ('noise_stop','operator_stop','start_requested',1),
    ('noise_foreign','error','start_requested',1),
    ('orb_foreign','already_running','error',0),
    ('orb_args','already_running','error',0),
    ('orb_workdir','already_running','error',0)])
def test_joint_wake_checks_each_bot_independently(tmp_path,case,noise_state,orb_state,count):
    noise=tmp_path/'qqq-noise-area';orb=tmp_path/'qqq-orb'
    for root in [noise,orb]:(root/'scripts').mkdir(parents=True);(root/'runtime/windows').mkdir(parents=True)
    (orb/'scripts/background_bootstrap.py').write_text('# synthetic only')
    shutil.copyfile(BOT/'wake-before-session.ps1',noise/'wake-before-session.ps1')
    (noise/'windows-common.ps1').write_text("$ErrorActionPreference='Stop'\n$qqqTaskName='TEST-NOISE'\nfunction Get-QqqPython { 'C:\\Python314\\pythonw.exe' }",encoding='utf-8-sig')
    if case=='noise_stop':(noise/'runtime/STOP_SHADOW.flag').touch()
    if case=='orb_stop':(orb/'runtime/STOP_SHADOW.flag').touch()
    (tmp_path/'exercise.ps1').write_text(r"""
$global:started=@()
function Get-ScheduledTask {
 param($TaskName,$ErrorAction)
 $orb=$TaskName -eq 'TradingBacktests-QQQ-ORB-Simulation'
 $root=Join-Path $PSScriptRoot $(if($orb){'qqq-orb'}else{'qqq-noise-area'})
 $state=if($orb -and 'CASE' -eq 'orb_disabled'){'Disabled'}elseif('CASE' -eq 'both_ready' -or ($orb -and 'CASE' -in @('orb_ready','noise_stop','noise_foreign'))){'Ready'}else{'Running'}
 $exe=if(($orb -and 'CASE' -eq 'orb_foreign') -or (-not $orb -and 'CASE' -eq 'noise_foreign')){'C:\foreign.exe'}else{'C:\Python314\pythonw.exe'}
 $arg='"'+(Join-Path $root 'scripts/background_bootstrap.py')+'" --runtime "'+(Join-Path $root 'runtime')+'"'
 if($orb -and 'CASE' -eq 'orb_args'){$arg+=' --paper'}
 $wd=if($orb -and 'CASE' -eq 'orb_workdir'){'C:\wrong'}else{$root}
 [pscustomobject]@{State=$state;Actions=@([pscustomobject]@{Execute=$exe;Arguments=$arg;WorkingDirectory=$wd})}
}
function Start-ScheduledTask {param($TaskName,$ErrorAction);$global:started+=,$TaskName;$global:started | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'starts.json')}
function Enable-ScheduledTask {throw 'must not override disabled task'}
& (Join-Path $PSScriptRoot 'qqq-noise-area/wake-before-session.ps1')
$global:started | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'starts.json')
""".replace('CASE',case),encoding='utf-8-sig')
    p=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(tmp_path/'exercise.ps1')],capture_output=True,text=True,timeout=20)
    status=json.loads((noise/'runtime/windows/wake_status.json').read_text(encoding='utf-8-sig'))
    assert status['bots']['noise']['state']==noise_state,(p.stdout,p.stderr,status)
    assert status['bots']['orb']['state']==orb_state,(p.stdout,p.stderr,status)
    starts_path=tmp_path/'starts.json';text=starts_path.read_text(encoding='utf-8-sig').strip() if starts_path.exists() else ''
    started=json.loads(text) if text else []
    if isinstance(started,str):started=[started]
    assert len(started)==count,(p.stdout,p.stderr,started)
    assert not list(tmp_path.rglob('*.sqlite'))
    assert (noise/'runtime/STOP_SHADOW.flag').exists()==(case=='noise_stop')
    assert (orb/'runtime/STOP_SHADOW.flag').exists()==(case=='orb_stop')
