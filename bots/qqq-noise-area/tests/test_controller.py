from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import pytest
from qqq_paper.strategy import Parameters,Session
from qqq_paper.ledger import Store
from qqq_paper.runner import Controller
from test_strategy import fixture
from test_execution import Broker,Executor
from test_ledger import filled


def test_shadow_uses_real_next_bar_open_and_never_calls_broker(tmp_path):
    m,s,f=fixture();p=Parameters();store=Store(tmp_path/'s.db',p,'shadow','sip');c=Controller(store,mode='shadow')
    f.iloc[30,f.columns.get_loc('open')]=106;f.iloc[30,f.columns.get_loc('high')]=106
    c.step(m,f,s,s.open+pd.Timedelta(minutes=31))
    assert store.position>0 and store.entry==106.01
    before=len(store.fills());c.step(m,f,s,s.open+pd.Timedelta(minutes=31))
    assert len(store.fills())==before
    c.step(m,f,s,s.close)
    assert store.position==0 and len(store.fills())==2


def test_utc_rest_payload_reaches_shadow_signal_and_costed_fill(tmp_path):
    from qqq_paper.alpaca import DataClient
    m,s,f=fixture();f.iloc[30,f.columns.get_loc('open')]=106;f.iloc[30,f.columns.get_loc('high')]=106
    rows=[dict(t=at.tz_convert('UTC').isoformat(),o=r.open,h=r.high,l=r.low,c=r.close,v=r.volume) for at,r in f.iloc[:31].iterrows()]
    class DataTransport:
        def request(self,*args,**kwargs):return dict(bars=rows)
    bars=DataClient(DataTransport()).bars(s.open,s.open+pd.Timedelta(minutes=31),'sip')
    assert str(bars.index.tz)=='UTC'
    store=Store(tmp_path/'s.db',Parameters(),'shadow','sip')
    Controller(store,mode='shadow').step(m,bars,s,s.open+pd.Timedelta(minutes=31))
    assert store.position>0 and store.entry==106.01
    assert not store.get('paused_day') and len(store.fills())==1


def test_paper_skips_expired_signals_and_flattens_without_current_bars(tmp_path):
    m,s,f=fixture();store=Store(tmp_path/'s.db',Parameters(),'paper','iex');b=Broker();e=Executor(store,b,wait_seconds=0)
    c=Controller(store,e,mode='paper');c.step(m,f,s,s.open+pd.Timedelta(minutes=31))
    assert not b.calls
    c.step(m,f,s,s.open+pd.Timedelta(minutes=60,seconds=5))
    assert store.position>0
    c.step(m,pd.DataFrame(),s,s.flatten)
    assert store.position==0 and b.calls[-1][0]=='close'


def test_current_missing_minute_pauses_day_and_closes_existing_position(tmp_path):
    m,s,f=fixture();store=Store(tmp_path/'s.db',Parameters(),'paper','iex');b=Broker();e=Executor(store,b,wait_seconds=0)
    c=Controller(store,e,mode='paper');c.step(m,f,s,s.open+pd.Timedelta(minutes=30,seconds=5))
    assert store.position>0
    bad=f.drop(f.index[35]);c.step(m,bad,s,s.open+pd.Timedelta(minutes=60,seconds=5))
    assert store.position==0 and store.get('paused_day')==str(s.open.date())


def test_external_position_mismatch_never_sends_new_orders(tmp_path):
    store=Store(tmp_path/'s.db',Parameters(),'paper','iex');b=Broker();b.position=lambda:100;b.open_orders=lambda:[]
    e=Executor(store,b);c=Controller(store,e,mode='paper')
    with pytest.raises(ValueError,match='external'):c.reconcile_live()
    assert not b.calls and store.position==0


def test_single_process_lock_blocks_second_instance(tmp_path):
    from qqq_paper.runtime import ProcessLock
    path=tmp_path/'bot.lock'
    with ProcessLock(path):
        with pytest.raises(RuntimeError):
            with ProcessLock(path):pass
    with ProcessLock(path):pass


def test_last_minute_publication_can_arrive_within_twenty_second_window(tmp_path):
    m,s,f=fixture();store=Store(tmp_path/'s.db',Parameters(),'paper','iex');b=Broker();e=Executor(store,b,wait_seconds=0)
    c=Controller(store,e,mode='paper');at=s.open+pd.Timedelta(minutes=30)
    c.step(m,f.drop(f.index[29]),s,at+pd.Timedelta(seconds=1))
    assert not b.calls and store.get('paused_day') is None
    c.step(m,f,s,at+pd.Timedelta(seconds=6))
    assert len(b.calls)==1 and store.position>0


def test_awaited_terminal_bar_expiring_pauses_day(tmp_path):
    m,s,f=fixture();store=Store(tmp_path/'s.db',Parameters(),'paper','iex');b=Broker();e=Executor(store,b,wait_seconds=0)
    c=Controller(store,e,mode='paper');at=s.open+pd.Timedelta(minutes=30);missing=f.drop(f.index[29])
    c.step(m,missing,s,at+pd.Timedelta(seconds=1))
    assert store.get('paused_day') is None
    c.step(m,missing,s,at+pd.Timedelta(seconds=21))
    assert not b.calls and store.get('paused_day')==str(s.open.date())
