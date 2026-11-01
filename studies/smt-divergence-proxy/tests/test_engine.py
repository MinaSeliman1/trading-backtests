from pathlib import Path
import sys
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from smt.engine import Config,make_plan,execute

def test_h1_plan_selects_priority_target_before_fill():
 a={k:np.full(720,v,float) for k,v in dict(open=100.,high=100.25,low=99.75,close=100.).items()}
 levels=[{'name':'London','ES':{'high':110.,'low':90.},'NQ':{'high':102.,'low':98.}},{'name':'Premarket','ES':{'high':111.,'low':89.},'NQ':{'high':103.,'low':97.}},{'name':'Previous','ES':{'high':112.,'low':88.},'NQ':{'high':104.,'low':96.}}]
 p=make_plan(a,levels,'H1',1,332,Config());assert p['status']=='eligible' and p['target']==102 and p['stop']==99.5

from smt.engine import scan

def bars():
 return {k:np.full(720,v,float) for k,v in dict(open=100.,high=100.25,low=99.75,close=100.).items()}
def levels():
 return [{'name':name,'ES':{'high':110.+i,'low':90.-i},'NQ':{'high':102.+i,'low':98.-i}} for i,name in enumerate(('London','Premarket','Previous'))]

def test_no_target_and_first_target_rr_rejection():
 a=bars();ls=levels()
 for x in ls:x['NQ']['high']=99.
 assert make_plan(a,ls,'H1',1,332,Config())['status']=='no_target'
 ls[0]['NQ']['high']=100.5;ls[1]['NQ']['high']=110.
 assert make_plan(a,ls,'H1',1,332,Config())['status']=='rr_below1'

def test_next_open_not_used_to_plan_and_gap_degrades_rr():
 a=bars();p=make_plan(a,levels(),'H1',1,332,Config());a['open'][332]=101.5;a['high'][332]=101.75;a['low'][332]=101.25;a['close'][332]=101.5
 assert make_plan(a,levels(),'H1',1,332,Config())==p
 x=execute(a,p,Config());assert x['entry_price']==101.75 and x['risk_points']==2.25 and x['gap_rr_below1'] and x['ecart_ouverture']==1.5
 assert x['net_r']==x['net_pnl']/4.5

@pytest.mark.parametrize('opening,reason',[(99.,'entry_marketable_stop'),(103.,'entry_marketable_target')])
def test_immediate_gap_exit_keeps_both_costs(opening,reason):
 a=bars();p=make_plan(a,levels(),'H1',1,332,Config());a['open'][332]=opening
 x=execute(a,p,Config());assert x['exit_reason']==reason and x['exit_reference']==opening and x['net_pnl']==-3.5

def test_stop_first_on_ambiguous_bar():
 a=bars();p=make_plan(a,levels(),'H1',1,332,Config());a['low'][332]=99.;a['high'][332]=103.
 x=execute(a,p,Config());assert x['ambiguous_stop_target'] and x['exit_reference']==99.5 and x['net_pnl']==-4.5

def test_forced_open_does_not_use_wicks():
 a=bars();p=make_plan(a,levels(),'H1',1,332,Config());a['low'][450]=1.;a['high'][450]=200.
 x=execute(a,p,Config());assert x['exit_reason']=='forced_1130' and x['exit_reference']==100. and x['net_pnl']==-3.5

def test_h2_target_based_on_actual_fill_and_stress_cost():
 a=bars();p=make_plan(a,levels(),'H2',1,332,Config());x=execute(a,p,Config());assert x['target']==101.75
 y=execute(a,make_plan(a,levels(),'H2',1,332,Config(slip_ticks_side=2)),Config(slip_ticks_side=2));assert y['net_pnl']==-4.5 and y['target']==102.5

def test_h1_scan_first_sweep_priority_and_prefix_causality():
 e=bars();a=bars();ls=levels();e['high'][332]=113.
 p=scan(e,a,ls,'H1',1,Config());assert p['entry_slot']==333 and p['source_level']=='London'
 a['open'][334:]=np.nan;e['high'][334:]=np.nan
 assert scan(e,a,ls,'H1',1,Config())==p

def test_equivalent_nq_sweep_prevents_signal():
 e=bars();a=bars();e['high'][332]=110.25;a['high'][330]=102.25
 assert scan(e,a,levels(),'H1',1,Config())['status']=='no_signal'

def test_h2_wait_reclaim_and_cancellation():
 e=bars();a=bars();e['low'][332]=89.75;e['open'][332]=90.;e['close'][332]=89.75;e['high'][332]=90.
 p=scan(e,a,levels(),'H2',1,Config());assert p['sweep_slot']==332 and p['entry_slot']==334
 a['low'][333]=97.75
 assert scan(e,a,levels(),'H2',1,Config())['status']=='smt_cancelled'

def test_sweep_before_window_does_not_retrigger():
 e=bars();a=bars();e['high'][330:333]=110.25
 assert scan(e,a,levels(),'H1',1,Config())['status']=='no_signal'

def test_short_execution_mirrors_long():
 a=bars();p=make_plan(a,levels(),'H1',1,332,Config());a['low'][332]=99.;x=execute(a,p,Config())
 b={'open':200-a['open'],'high':200-a['low'],'low':200-a['high'],'close':200-a['close']}
 ls=levels()
 for lev in ls:
  for symbol in ('ES','NQ'):lev[symbol]={'high':200-lev[symbol]['low'],'low':200-lev[symbol]['high']}
 q=make_plan(b,ls,'H1',-1,332,Config());y=execute(b,q,Config());assert x['net_pnl']==y['net_pnl'] and x['net_r']==y['net_r']

def test_c_same_bar_two_sides_is_ambiguous():
 e=bars();a=bars();e['high'][332]=110.25;e['low'][332]=89.75
 assert scan(e,a,levels(),'H1',None,Config())['status']=='ambiguous_same_bar'


def test_detection_level_diagnostic_keeps_pooled_target_priority():
 e=bars();a=bars();ls=levels();e['high'][332]=113.
 p=scan(e,a,[ls[2]],'H1',1,Config(),plan_levels=ls)
 assert p['source_level']=='Previous' and p['target_level']=='London' and p['target']==102.

def test_h2_does_not_arm_on_0930():
 e=bars();a=bars();e['low'][330]=89.75
 assert scan(e,a,levels(),'H2',1,Config())['status']=='no_signal'


def test_zero_real_risk_is_explicit_not_free_trade():
 a=bars();p=make_plan(a,levels(),'H1',1,332,Config());a['open'][332]=99.25
 x=execute(a,p,Config());assert x['zero_risk'] and x['net_r'] is None and x['net_pnl']==-3.5
