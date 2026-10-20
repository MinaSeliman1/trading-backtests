from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import pytest
from qqq_paper import windows_setup as setup
from qqq_paper.alpaca import APIError


class Vault:
    def __init__(self):self.saved=None
    def save(self,*values):self.saved=values


def test_setup_rejected_account_does_not_store_or_echo_keys(tmp_path,monkeypatch,capsys):
    class Transport:
        def __init__(self,*args):pass
        def request(self,*args,**kwargs):raise APIError(401,'GET','/v2/account')
        def clear(self):pass
    values=iter(['private-id','private-secret']);monkeypatch.setattr(setup.getpass,'getpass',lambda _:next(values))
    monkeypatch.setattr(setup,'Transport',Transport);v=Vault()
    with pytest.raises(APIError):setup.configure(tmp_path,v)
    assert v.saved is None and 'private-secret' not in capsys.readouterr().out


def test_setup_checks_only_get_requests_then_saves_in_windows_vault(tmp_path,monkeypatch):
    calls=[]
    class Transport:
        def __init__(self,*args):pass
        def request(self,origin,path,method='GET',**kwargs):
            calls.append((path,method))
            if path=='/v2/account':return dict(id='A',status='ACTIVE',equity='100000')
            if path=='/v2/clock':return dict(timestamp='2026-10-20T20:40:00Z')
            if path.endswith('/bars'):return dict(bars=[])
            pytest.fail(path)
        def clear(self):pass
    values=iter(['test-id','test-secret']);monkeypatch.setattr(setup.getpass,'getpass',lambda _:next(values))
    monkeypatch.setattr(setup,'Transport',Transport);v=Vault();setup.configure(tmp_path,v)
    assert v.saved==('test-id','test-secret') and all(method=='GET' for _,method in calls)
    status=json.loads((tmp_path/'windows/setup.json').read_text())
    assert status['state']=='windows_credentials_configured' and 'test-secret' not in (tmp_path/'windows/setup.json').read_text()
