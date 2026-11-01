from pathlib import Path
from types import SimpleNamespace
import json
import numpy as np
import pandas as pd
import pytest
from qqq_eod import source,replay

@pytest.fixture(scope='module',autouse=True)
def pinned(pinned_sources):return pinned_sources

def session(half=False):
 day='2026-11-27' if half else '2026-10-30'
 return SimpleNamespace(open=pd.Timestamp(day+' 09:30',tz='America/New_York'),close=pd.Timestamp(day+(' 13:00' if half else ' 16:00'),tz='America/New_York'))

def bars(s,short=False):
 idx=pd.date_range(s.open,s.close-pd.Timedelta(minutes=1),freq='min');n=len(idx)
 f=pd.DataFrame(dict(open=np.full(n,100.),high=np.full(n,100.2),low=np.full(n,99.8),close=np.full(n,100.),volume=np.full(n,1000.)),index=idx)
 f.iloc[:5,f.columns.get_loc('open')]=100.5 if short else 99.5
 f.iloc[:5,f.columns.get_loc('high')]=101 if short else 100.5;f.iloc[:5,f.columns.get_loc('low')]=99.5 if short else 99
 f.iloc[-1,:4]=[99,100,98,99] if short else [101,102,100,101]
 return f

def history(s):
 dates=pd.bdate_range(end=s.open.tz_localize(None).normalize()-pd.Timedelta(days=1),periods=16)
 return SimpleNamespace(dates=dates,arrays={k:np.full((16,390),1000. if k=='volume' else 100.) for k in ('open','high','low','close','volume')},lengths=np.full(16,390),valid=np.ones(16,bool))

@pytest.mark.parametrize('short,expected',[(False,9.1),(True,9.072225)])
def test_orb_same_frozen_costs_and_causal_path(short,expected):
 s=session();x=replay.orb(bars(s,short),s,1000.)
 assert x['status']=='complete' and x['net_pnl']==pytest.approx(expected) and x['capital_after']==pytest.approx(1000+expected)
 assert not x['operationally_observed'] and x['trades'][0]['quantity']==10

def test_orb_halfday_and_stop_priority():
 s=session(True);f=bars(s);f.iloc[10,:4]=[100,111,98,100]
 x=replay.orb(f,s,1000);assert x['trades'][0]['exit_reason']=='stop_intrabar' and x['trades'][0]['exit_reference']==99
 y=replay.orb(bars(s),s,1000);assert pd.Timestamp(y['trades'][0]['exit_time']).strftime('%H:%M')=='12:59'

def test_missing_bar_preserves_known_fee_and_blocks_not_cash():
 s=session();f=bars(s).drop(s.open+pd.Timedelta(minutes=7));x=replay.orb(f,s,1000)
 assert x['status']=='unresolved' and x['net_pnl'] is None and x['open_position']!=0
 assert x['known_balance']==pytest.approx(999.65) and x['known_commission']==pytest.approx(.35)

def test_noise_matches_unchanged_controller_and_prefixes(tmp_path,monkeypatch):
 from qqq_paper.strategy import Parameters,Session
 from qqq_paper.runner import Controller
 from qqq_paper.ledger import Store
 s0=session();s=Session(s0.open,s0.close);f=bars(s);h=history(s);f['close']=100.05;f.iloc[-1,:4]=[101,102,100,101]
 reference=Store(tmp_path/'reference.sqlite',Parameters(initial_capital=1000),'shadow','sip');Controller(reference,mode='shadow').step(h,f,s,s.close);want=reference.balance;reference.close()
 original=Controller.step;seen=[]
 def checked(self,hist,frame,sess,asof,*args,**kwargs):
  assert frame.empty or frame.index.max()<asof
  assert pd.Timestamp(hist.dates[-1]).date()<sess.open.date()
  seen.append(asof);return original(self,hist,frame,sess,asof,*args,**kwargs)
 monkeypatch.setattr(Controller,'step',checked)
 x=replay.noise(h,f,s,1000,workdir=tmp_path/'run')
 assert x['status']=='complete' and x['capital_after']==pytest.approx(want) and x['net_pnl']==pytest.approx(want-1000)
 assert len(x['decisions'])==12 and len(seen)==13 and not x['operationally_observed']
 assert all('engine_asof' in d and 'observed_at' not in d for d in x['decisions'])

def test_history_gap_not_successful_zero(tmp_path):
 from qqq_paper.strategy import Session
 s0=session();s=Session(s0.open,s0.close);h=history(s);h.valid[-1]=False
 x=replay.noise(h,bars(s),s,1000,workdir=tmp_path)
 assert x['status']=='unresolved' and x['net_pnl'] is None

def test_orb_capital_is_an_input_not_live_account():
 s=session();a=replay.orb(bars(s),s,1000);b=replay.orb(bars(s),s,2000)
 assert a['trades'][0]['quantity']==10 and b['trades'][0]['quantity']==20


def test_orb_supplies_only_new_closed_bars_to_frozen_cache(monkeypatch):
 from orb_shadow import core
 original=core.advance;counts=[]
 def checked(account,day,frame,session,asof):
  assert len(frame)<=5 if day is None else len(frame)<=1
  assert frame.empty or frame.index.max()<asof
  counts.append(len(frame));return original(account,day,frame,session,asof)
 monkeypatch.setattr(core,'advance',checked)
 s=session();x=replay.orb(bars(s),s,1000)
 assert x['net_pnl']==pytest.approx(9.1) and counts[0]==5 and len(counts)>100
