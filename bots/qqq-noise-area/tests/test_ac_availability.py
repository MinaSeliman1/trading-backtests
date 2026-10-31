"""Exercise the AC plan helper against a stateful fake powercfg only."""
from pathlib import Path
import json,shutil,subprocess,os
import pytest
BOT=Path(__file__).resolve().parents[1]

def exercise(tmp,case='apply'):
    shutil.copyfile(BOT/'configure-ac-availability.ps1',tmp/'configure-ac-availability.ps1')
    ps=r"""
$ErrorActionPreference='Stop'
$global:calls=@();$global:failed=$false
$global:values=@{RTCWAKE=@(2,0);STANDBYIDLE=@(900,600);HIBERNATEIDLE=@(10800,10800)}
function powercfg {
 $global:calls+=,($args -join ' ');$global:LASTEXITCODE=0
 if($args[0] -eq '/getactivescheme'){'GUID: 381b4222-f694-41f0-9685-ff5bb260df2e';return}
 if($args[0] -eq '/query') {
   if('CASE' -eq 'bad_read' -and $args[3] -eq 'HIBERNATEIDLE'){$global:LASTEXITCODE=1;return}
   $v=$global:values[$args[3]]
   if($args[3] -ne 'RTCWAKE'){'Minimum: 0x00000000';'Maximum: 0xffffffff'}
   'AC: 0x'+$v[0].ToString('x8');'DC: 0x'+$v[1].ToString('x8');return
 }
 if($args[0] -eq '/setacvalueindex') {
   if('CASE' -eq 'fail_write' -and $args[3] -eq 'HIBERNATEIDLE' -and -not $global:failed){$global:failed=$true;$global:LASTEXITCODE=5;return}
   $global:values[$args[3]][0]=[int]$args[4];return
 }
 if($args[0] -eq '/setactive'){return}
 throw 'Unexpected mutation or command'
}
if('CASE' -eq 'proof_error') {New-Item -ItemType Directory -Path (Join-Path $PSScriptRoot 'runtime/windows/ac_availability_current.json') -Force | Out-Null}
$ok=$true
try {
 if('CASE' -eq 'audit') {& (Join-Path $PSScriptRoot 'configure-ac-availability.ps1') | Out-Null}
 else {& (Join-Path $PSScriptRoot 'configure-ac-availability.ps1') -Apply | Out-Null}
 if('CASE' -eq 'twice') {& (Join-Path $PSScriptRoot 'configure-ac-availability.ps1') -Apply | Out-Null}
} catch {$ok=$false}
[ordered]@{ok=$ok;calls=$global:calls;values=$global:values}|ConvertTo-Json -Depth 6|Set-Content -LiteralPath (Join-Path $PSScriptRoot 'proof.json') -Encoding UTF8
""".replace('CASE',case)
    (tmp/'exercise.ps1').write_text(ps,encoding='utf-8-sig')
    p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(tmp/'exercise.ps1')],capture_output=True,text=True,timeout=25)
    assert p.returncode==0,p.stdout+p.stderr
    return json.loads((tmp/'proof.json').read_text(encoding='utf-8-sig'))

@pytest.mark.skipif(os.name!='nt',reason='Windows policy helper')
def test_apply_changes_ac_only_with_numeric_metadata_and_backup(tmp_path):
    p=exercise(tmp_path)
    assert p['ok'] and p['values']=={'RTCWAKE':[1,0],'STANDBYIDLE':[0,600],'HIBERNATEIDLE':[0,10800]}
    assert not any('/setdc' in s or '/hibernate' in s for s in p['calls'])
    backup=list((tmp_path/'runtime/windows').glob('ac_availability_before-*.json'));assert len(backup)==1
    b=json.loads(backup[0].read_text(encoding='utf-8-sig'))
    assert b['settings']['STANDBYIDLE']['ac']==900 and b['settings']['HIBERNATEIDLE']['dc']==10800

@pytest.mark.skipif(os.name!='nt',reason='Windows policy helper')
def test_default_is_read_only_and_does_not_create_runtime(tmp_path):
    p=exercise(tmp_path,'audit');assert p['ok'];assert all('/set' not in s for s in p['calls']);assert not (tmp_path/'runtime').exists()

@pytest.mark.skipif(os.name!='nt',reason='Windows policy helper')
def test_repeat_keeps_first_backup_and_is_idempotent(tmp_path):
    p=exercise(tmp_path,'twice');assert p['ok']
    b=json.loads(next((tmp_path/'runtime/windows').glob('ac_availability_before-*.json')).read_text(encoding='utf-8-sig'))
    assert b['settings']['STANDBYIDLE']['ac']==900
    assert sum('/setacvalueindex' in s for s in p['calls'])==3

@pytest.mark.skipif(os.name!='nt',reason='Windows policy helper')
def test_read_failure_happens_before_any_mutation(tmp_path):
    p=exercise(tmp_path,'bad_read');assert not p['ok'];assert all('/set' not in s for s in p['calls'])

@pytest.mark.skipif(os.name!='nt',reason='Windows policy helper')
def test_partial_write_failure_restores_original_ac_and_keeps_dc(tmp_path):
    p=exercise(tmp_path,'fail_write');assert not p['ok']
    assert p['values']=={'RTCWAKE':[2,0],'STANDBYIDLE':[900,600],'HIBERNATEIDLE':[10800,10800]}
    assert not any('/setdc' in s for s in p['calls'])


@pytest.mark.skipif(os.name!='nt',reason='Windows policy helper')
def test_proof_write_failure_rolls_back_applied_settings(tmp_path):
    p=exercise(tmp_path,'proof_error');assert not p['ok']
    assert p['values']=={'RTCWAKE':[2,0],'STANDBYIDLE':[900,600],'HIBERNATEIDLE':[10800,10800]}
    assert sum('/setacvalueindex' in s for s in p['calls'])==6
