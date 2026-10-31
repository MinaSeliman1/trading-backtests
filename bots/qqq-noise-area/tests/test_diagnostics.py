"""Fatal diagnostics: never serialize exception messages, source or credentials."""
from pathlib import Path
import json,sys,runpy
from types import ModuleType
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from qqq_paper import diagnostics as d

def setup(tmp,monkeypatch):
    monkeypatch.setenv('LOCALAPPDATA',str(tmp/'local'))
    return tmp/'runtime'
def value(root):return json.loads((root/'windows/last_fatal.json').read_text(encoding='utf-8'))
def test_exception_type_errno_and_stack_without_message_or_source(tmp_path,monkeypatch):
    root=setup(tmp_path,monkeypatch)
    def broken():raise PermissionError(13,'PRIVATE-SECRET-NEVER-SAVE')
    assert d.run(broken,root,'noise')==1
    v=value(root);assert v['error_type']=='PermissionError' and v['errno']==13 and v['frames'][-1]['function']=='broken'
    assert 'PRIVATE-SECRET' not in json.dumps(v) and all(set(x)=={'file','line','function'} for x in v['frames'])
def test_fallback_is_outside_onedrive_if_runtime_write_fails(tmp_path,monkeypatch):
    root=setup(tmp_path,monkeypatch);real=d._write
    def write(path,v):
        if root in path.parents:raise PermissionError('PRIVATE-SECRET')
        return real(path,v)
    monkeypatch.setattr(d,'_write',write)
    assert d.run(lambda:1,root,'orb')==1
    p=tmp_path/'local/TradingBacktests/Diagnostics/orb/last_fatal.json';assert p.exists() and json.loads(p.read_text())['exit_code']==1
def test_failed_diagnostic_write_keeps_failure_code_and_no_output(tmp_path,monkeypatch,capsys):
    root=setup(tmp_path,monkeypatch)
    def fail(*a):raise PermissionError('PRIVATE-SECRET')
    monkeypatch.setattr(d,'_write',fail)
    assert d.run(lambda:1,root,'noise')==1
    assert 'PRIVATE-SECRET' not in str(capsys.readouterr())
def test_normal_exit_does_not_invent_failure(tmp_path,monkeypatch):
    root=setup(tmp_path,monkeypatch);assert d.run(lambda:0,root,'noise')==0
    assert not (root/'windows/last_fatal.json').exists()
def test_system_exit_text_is_not_logged(tmp_path,monkeypatch):
    root=setup(tmp_path,monkeypatch)
    def bad():raise SystemExit('PRIVATE-SECRET')
    assert d.run(bad,root,'orb')==1 and 'PRIVATE-SECRET' not in json.dumps(value(root))
def test_pythonw_missing_console_is_supported(tmp_path,monkeypatch):
    root=setup(tmp_path,monkeypatch)
    with monkeypatch.context() as m:
        m.setattr(sys,'stdout',None);m.setattr(sys,'stderr',None)
        assert d.run(lambda:1,root,'orb')==1
    assert value(root)['exit_code']==1
def test_hidden_runtime_error_is_preserved_instead_of_generic_exit(tmp_path,monkeypatch):
    from qqq_paper import background
    root=setup(tmp_path,monkeypatch)
    def bad(*a):raise RuntimeError('PRIVATE-SECRET')
    monkeypatch.setattr(background,'serve',bad)
    assert d.run(lambda:background.main(['--runtime',str(root)]),root,'noise')==1
    assert value(root)['error_type']=='RuntimeError' and value(root)['frames'][-1]['function']=='bad'
@pytest.mark.parametrize('component,module',[('noise','qqq_paper.background'),('orb','orb_shadow.service')])
def test_real_bootstrap_captures_fatal_before_any_broker_call(tmp_path,monkeypatch,component,module):
    root=setup(tmp_path,monkeypatch);fake=ModuleType(module)
    def main():raise OSError(5,'PRIVATE-SECRET')
    fake.main=main;monkeypatch.setitem(sys.modules,module,fake);monkeypatch.setattr(sys,'argv',['launcher','--runtime',str(root)])
    bots=Path(__file__).resolve().parents[2];script=bots/('qqq-noise-area' if component=='noise' else 'qqq-orb')/'scripts/background_bootstrap.py'
    with pytest.raises(SystemExit) as e:runpy.run_path(str(script),run_name='__main__')
    assert e.value.code==1 and value(root)['errno']==5


@pytest.mark.parametrize('arguments',[
    ['--runtime','chosen'],['--runtime=chosen'],['--runtime','first','--runtime=chosen']])
def test_runtime_location_matches_argparse_forms_and_last_value(arguments):
    assert d.runtime_from_args(arguments,Path('default'))==Path('chosen')
