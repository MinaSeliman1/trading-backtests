from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import pytest
import pandas as pd
from qqq_paper.ledger import Store
from qqq_paper.strategy import Parameters
from qqq_paper.runtime import ProcessLock,session_for
from qqq_paper.runner import Controller,Executor
from qqq_paper import __main__ as app
from test_execution import Broker
from test_ledger import filled


def test_shadow_does_not_silently_carry_a_missed_previous_close(tmp_path):
    s=Store(tmp_path/'s.db',Parameters(),'shadow','sip')
    s.intent('old','2026-10-19','open',1,100,'10:00')
    snapshot=filled('old',100,100);snapshot['filled_at']='2026-10-19T14:00:00Z';s.apply(snapshot)
    session=session_for('2026-10-20')
    with pytest.raises(ValueError,match='prior session'):
        Controller(s,mode='shadow').step(None,pd.DataFrame(),session,session.open+pd.Timedelta(minutes=1))
    assert s.get('paused') and s.position==100 and len(s.fills())==1


def test_inherited_position_closed_at_open_without_market_data(tmp_path):
    s=Store(tmp_path/'s.db',Parameters(),'paper','iex');b=Broker();e=Executor(s,b,wait_seconds=0)
    s.intent('old','2026-10-16','open',1,100,'10:00');x=filled('old',100,100);x['filled_at']='2026-10-16T14:00:00Z';s.apply(x)
    session=session_for('2026-10-19');c=Controller(s,e,mode='paper')
    c.step(None,pd.DataFrame(),session,session.open+pd.Timedelta(minutes=1))
    assert s.position==0 and s.get('paused') and b.calls==[('close',-1,100)]


def interrupt_case(tmp_path,monkeypatch,check):
    folder=tmp_path/'paper-iex';folder.mkdir();s=Store(folder/'state.sqlite',Parameters(),'paper','iex')
    s.intent('old','2026-10-20','open',1,100,'10:00');s.apply(filled('old',100,100));s.close()
    class FakeTransport:
        def __init__(self,*args):pass
        def clear(self):pass
    class FakeBroker:
        def __init__(self,*args):pass
        def account(self):return dict(id='A',status='ACTIVE',equity='100000')
        def clock(self):return dict(timestamp='2026-10-20T14:15:00Z',is_open=True)
    class FakeData:
        def __init__(self,*args):pass
        def bars(self,*args):raise KeyboardInterrupt()
    monkeypatch.setenv('ALPACA_PAPER_KEY_ID','test');monkeypatch.setenv('ALPACA_PAPER_SECRET_KEY','test')
    monkeypatch.setattr(app,'Transport',FakeTransport);monkeypatch.setattr(app,'PaperBroker',FakeBroker);monkeypatch.setattr(app,'DataClient',FakeData)
    monkeypatch.setattr(app.Controller,'reconcile_live',lambda *args,**kwargs:None)
    calls=[]
    def close(controller,*args):
        calls.append('close')
        with pytest.raises(RuntimeError):
            with ProcessLock(tmp_path/'paper.lock'):pass
    monkeypatch.setattr(app.Controller,'_flatten_paper',close)
    monkeypatch.setattr(app,'load_history',lambda *args:(_ for _ in ()).throw(KeyboardInterrupt()))
    code=app.main(['--mode','paper','--feed','iex','--runtime',str(tmp_path)]+(['--check'] if check else []))
    assert code==0
    return calls


def test_read_only_check_interrupt_never_cancels_or_closes(tmp_path,monkeypatch):
    assert interrupt_case(tmp_path,monkeypatch,True)==[]


def test_process_lock_held_through_interrupt_cleanup(tmp_path,monkeypatch):
    assert interrupt_case(tmp_path,monkeypatch,False)==['close']


@pytest.mark.parametrize('stage',['preflight','first_clock'])
def test_early_interrupt_has_no_uninitialized_cleanup(tmp_path,monkeypatch,stage):
    class FakeTransport:
        def __init__(self,*args):pass
        def clear(self):pass
    class FakeBroker:
        def __init__(self,*args):self.clocks=0
        def account(self):
            if stage=='preflight':raise KeyboardInterrupt()
            return dict(id='A',status='ACTIVE',equity='100000')
        def clock(self):
            self.clocks+=1
            if self.clocks==1:raise KeyboardInterrupt()
            return dict(timestamp='2026-10-20T14:15:00Z',is_open=True)
    monkeypatch.setenv('ALPACA_PAPER_KEY_ID','test');monkeypatch.setenv('ALPACA_PAPER_SECRET_KEY','test')
    monkeypatch.setattr(app,'Transport',FakeTransport);monkeypatch.setattr(app,'PaperBroker',FakeBroker)
    calls=[]
    monkeypatch.setattr(app.Controller,'reconcile_live',lambda *args,**kwargs:calls.append('reconcile'))
    monkeypatch.setattr(app.Controller,'_flatten_paper',lambda *args:calls.append('close'))
    assert app.main(['--mode','paper','--feed','iex','--runtime',str(tmp_path),'--once'])==0
    assert calls==([] if stage=='preflight' else ['reconcile','close'])
    assert json.loads((tmp_path/'paper-iex/status.json').read_text())['state']=='stopped'


def test_restart_partial_order_at_flatten_cancels_and_closes_without_data(tmp_path,monkeypatch):
    folder=tmp_path/'paper-iex';folder.mkdir();s=Store(folder/'state.sqlite',Parameters(),'paper','iex')
    cid=Executor.cid('2026-10-20','1530','open',1);s.intent(cid,'2026-10-20','open',1,100,'1530');s.close()
    b=Broker();b.orders[cid]=filled(cid,40,100,'partially_filled')
    b.account=lambda:dict(id='A',status='ACTIVE',equity='100000')
    b.clock=lambda:dict(timestamp='2026-10-20T19:59:01Z',is_open=True)
    b.position=lambda:40 if not b.calls else 0
    b.open_orders=lambda:[o for o in b.orders.values() if o['status']=='partially_filled']
    class FakeTransport:
        def __init__(self,*args):pass
        def clear(self):pass
    monkeypatch.setenv('ALPACA_PAPER_KEY_ID','test');monkeypatch.setenv('ALPACA_PAPER_SECRET_KEY','test')
    monkeypatch.setattr(app,'Transport',FakeTransport);monkeypatch.setattr(app,'PaperBroker',lambda _:b)
    monkeypatch.setattr(app,'load_history',lambda *args:pytest.fail('closing must not fetch data'))
    assert app.main(['--mode','paper','--feed','iex','--runtime',str(tmp_path),'--once'])==0
    state=json.loads((folder/'status.json').read_text())
    assert state['managed_qty']==0 and b.orders[cid]['status']=='canceled' and b.calls==[('close',-1,40)]
