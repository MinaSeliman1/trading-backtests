from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
from contextlib import nullcontext
import pytest
from qqq_paper import background
from qqq_paper import __main__ as app
from qqq_paper.windows_vault import CredentialError


@pytest.fixture(autouse=True)
def isolate_windows_power_api(monkeypatch):
    # These tests exercise the supervisor; never change the test machine's power request.
    monkeypatch.setattr(background,'PowerGuard',lambda runtime:nullcontext(),raising=False)


def test_hidden_launcher_is_fixed_shadow_sip_and_stops_cleanly(tmp_path,monkeypatch):
    class Vault:
        def load(self):return ('test-id','test-secret')
    calls=[]
    def application(argv,credentials=None):
        calls.append((app.arguments(argv),credentials));(tmp_path/'STOP_SHADOW.flag').touch();return 0
    monkeypatch.setattr(background,'WindowsVault',Vault);monkeypatch.setattr(background.app,'main',application)
    assert background.serve(tmp_path)==0
    assert len(calls)==1 and calls[0][0].mode=='shadow' and calls[0][0].feed=='sip'
    assert calls[0][1]==('test-id','test-secret')
    state=json.loads((tmp_path/'windows/status.json').read_text());assert state['state']=='stopped'
    assert 'test-secret' not in (tmp_path/'windows/background.log').read_text()


def test_missing_vault_never_logs_secret_or_runs_application(tmp_path,monkeypatch):
    class Vault:
        def load(self):
            (tmp_path/'STOP_SHADOW.flag').touch();raise CredentialError('private-secret-must-not-appear')
    monkeypatch.setattr(background,'WindowsVault',Vault)
    monkeypatch.setattr(background.app,'main',lambda *a,**k:pytest.fail('no application without credential'))
    assert background.serve(tmp_path)==0
    assert 'private-secret' not in (tmp_path/'windows/background.log').read_text()


def test_background_retries_startup_failure_without_changing_state_directory(tmp_path,monkeypatch):
    class Vault:
        def load(self):return ('test-id','test-secret')
    calls=[];retry_markers=[]
    def application(argv,credentials=None):
        calls.append(app.arguments(argv))
        if len(calls)==2:(tmp_path/'STOP_SHADOW.flag').touch();return 0
        return 1
    monkeypatch.setattr(background,'WindowsVault',Vault);monkeypatch.setattr(background.app,'main',application)
    def retry_wait(*args):
        retry_markers.append(json.loads((tmp_path/'windows/status.json').read_text()).get('power_guard'))
        return False
    monkeypatch.setattr(background,'wait_for_stop',retry_wait)
    assert background.serve(tmp_path)==0 and len(calls)==2
    assert all(c.runtime==tmp_path for c in calls)
    assert retry_markers==[True]


def test_stop_file_option_is_refused_for_paper_orders(tmp_path):
    with pytest.raises(SystemExit):app.arguments(['--mode','paper','--stop-file',str(tmp_path/'STOP')])


def test_shadow_stop_file_preserves_state_and_never_fetches_bars(tmp_path,monkeypatch):
    stop=tmp_path/'STOP';stop.touch()
    class Transport:
        def __init__(self,*args):pass
        def clear(self):pass
    class Broker:
        def __init__(self,*args):pass
        def account(self):return dict(id='A',status='ACTIVE',equity='100000')
        def clock(self):return dict(timestamp='2026-10-20T20:40:00Z',is_open=False)
    monkeypatch.setattr(app,'Transport',Transport);monkeypatch.setattr(app,'PaperBroker',Broker)
    monkeypatch.setattr(app,'load_history',lambda *a:pytest.fail('stop precedes data loading'))
    assert app.main(['--mode','shadow','--feed','sip','--runtime',str(tmp_path),'--stop-file',str(stop)],credentials=('test-id','test-secret'))==0
    assert json.loads((tmp_path/'shadow-sip/status.json').read_text())['state']=='stopped'


def test_post_fetch_clock_records_late_observation_without_advancing_data_cutoff(tmp_path,monkeypatch):
    import pandas as pd
    seen={}
    class Clock:
        @staticmethod
        def now(tz):return pd.Timestamp('2026-10-21T20:25:00Z').to_pydatetime()
    class Transport:
        def __init__(self,*args):pass
        def clear(self):pass
    class Broker:
        def __init__(self,*args):pass
        def account(self):return dict(id='A',status='ACTIVE',equity='100000')
        def clock(self):return dict(timestamp='2026-10-21T20:16:00Z',is_open=False)
    class Data:
        def __init__(self,*args):pass
        def bars(self,*args):return pd.DataFrame()
        def dividend(self,*args):return 0
    class Controller:
        def __init__(self,*args):pass
        def step(self,history,bars,session,asof,dividend,observation_clock=None):seen.update(asof=asof,observed_at=observation_clock())
    monkeypatch.setattr(app,'Transport',Transport);monkeypatch.setattr(app,'PaperBroker',Broker)
    monkeypatch.setattr(app,'DataClient',Data);monkeypatch.setattr(app,'Controller',Controller)
    monkeypatch.setattr(app,'datetime',Clock);monkeypatch.setattr(app,'load_history',lambda *args:None)
    assert app.main(['--once','--runtime',str(tmp_path)],credentials=('test-id','test-secret'))==0
    assert seen['asof']==pd.Timestamp('2026-10-21T20:00:00Z')
    assert seen['observed_at']==pd.Timestamp('2026-10-21T20:09:00Z')


def test_graceful_shadow_stop_preserves_existing_balance_and_open_position(tmp_path,monkeypatch):
    from qqq_paper.ledger import Store
    from qqq_paper.strategy import Parameters
    path=tmp_path/'shadow-sip/state.sqlite'
    store=Store(path,Parameters(),'shadow','sip')
    account=dict(balance=98765.43,position=23,entry=400.01,entry_timestamp='2026-10-21T14:00:00+00:00')
    with store.db:store._save_account(account);store.put('paper_account_id','A')
    store.close();stop=tmp_path/'STOP';stop.touch()
    class Transport:
        def __init__(self,*args):pass
        def clear(self):pass
    class Broker:
        def __init__(self,*args):pass
        def account(self):return dict(id='A',status='ACTIVE',equity='100000')
        def clock(self):return dict(timestamp='2026-10-21T14:30:00Z',is_open=True)
    monkeypatch.setattr(app,'Transport',Transport);monkeypatch.setattr(app,'PaperBroker',Broker)
    assert app.main(['--runtime',str(tmp_path),'--stop-file',str(stop)],credentials=('test-id','test-secret'))==0
    resumed=Store(path,Parameters(),'shadow','sip')
    assert resumed._account()==account and not resumed.fills()


def test_supervisor_owns_power_protection_before_api_work_and_releases_on_stop(tmp_path,monkeypatch):
    import pandas as pd
    from qqq_paper.power import PowerGuard
    class Power:
        required=False
        def on_ac(self):return True
        def system_required(self,enabled):self.required=enabled
    class Vault:
        def load(self):return ('test-id','test-secret')
    power=Power()
    observed=[]
    monkeypatch.setattr(background,'PowerGuard',lambda runtime:PowerGuard(runtime,backend=power,clock=lambda:pd.Timestamp('2026-10-23T15:00:00Z')))
    monkeypatch.setattr(background,'WindowsVault',Vault)
    def application(argv,credentials=None):
        (tmp_path/'STOP_SHADOW.flag').touch()
        observed.append(power.required)
        return 0
    monkeypatch.setattr(background.app,'main',application)
    assert background.serve(tmp_path)==0
    assert observed==[True] and not power.required
