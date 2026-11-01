from pathlib import Path
from types import SimpleNamespace
import sys,math
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dip.engine import Config,history,prepare,select,trace,simulate,Unresolved

def market(days=23):
 a={k:np.full((days,390),v,float) for k,v in dict(open=100.,high=102.,low=98.,close=99.,volume=1000.).items()}
 for k,v in dict(open=100.,high=101.,low=98.5,close=100.).items():a[k][-1,:]=v
 a['close'][-1,4]=98.9;a['low'][-1,5:389]=99.5
 for k,v in dict(open=101.,high=101.5,low=100.5,close=101.).items():a[k][-1,389]=v
 dates=pd.bdate_range(end='2024-02-06',periods=days)
 return SimpleNamespace(symbol='SPY',dates=dates,arrays=a,lengths=np.full(days,390),valid=np.ones(days,bool),
  quality=pd.DataFrame({'session_open':[str(d.date())+' 09:30:00-05:00' for d in dates],'reason':['']*days}))

def feature():
 return dict(index=22,date='2024-02-06',session_minutes=390,reason='eligible',average_drop=1.,adr=4.,previous_close=99.,previous_red_count=2,
  opening_price=100.,dip_level=99.,stop_price=99.,bar_index=20,decision_slot=105,signal_slot=104,entry_slot=106,sizing_price=100.)

def run(m=None,c=None,f=None):
 m=m or market();f=f or feature();return simulate(m,[f],c or Config(),f['date'],f['date'])

def bar(m,j,**kw):
 for k,v in kw.items():m.arrays[k][-1,j]=v

def test_estimator_includes_zero_green_days_and_excludes_today():
 m=market();m.arrays['close'][:-1,:]=101.;m.arrays['close'][0,389]=98.
 h=history(m,Config());assert h[21]['average_drop']==pytest.approx(2/21) and h[22]['average_drop']==0

def test_drop_is_body_not_low_or_conditional_red_mean():
 m=market();m.arrays['close'][2,389]=101.;assert history(m,Config())[-1]['average_drop']==pytest.approx(20/21)
 m.arrays['low'][:-1,:]=1.;assert history(m,Config())[-1]['average_drop']==pytest.approx(20/21)

def test_adr_uses_previous_fourteen_ranges():
 h=history(market(),Config());assert h[-1]['adr']==4 and h[20]['history_reason']=='warmup' and h[21]['history_reason']=='ready'

def test_current_afternoon_never_enters_history_or_first_signal():
 m=market();a=select(m,22,Config())
 for k in ('open','high','low','close'):m.arrays[k][-1,100:]=1000.
 assert select(m,22,Config())==a

def test_history_does_not_skip_gap():
 m=market();m.arrays['volume'][5,50]=np.nan;m.valid[5]=False;assert history(m,Config())[-1]['history_reason']=='unknown_history'

def test_current_future_invalid_flag_keeps_early_signal():
 m=market();a=select(m,22,Config());bar(m,250,volume=np.nan);m.valid[-1]=False;m.quality.loc[22,'reason']='missing_minutes|invalid_ohlcv'
 assert select(m,22,Config())==a

def test_past_half_session_uses_real_length():
 m=market();m.lengths[10]=210
 for k in m.arrays:m.arrays[k][10,210:]=np.nan
 assert history(m,Config())[-1]['adr']==4 and history(m,Config())[-1]['average_drop']==1

def test_no_red_bodies_known_inactivity():
 m=market();m.arrays['close'][:-1,:]=101.;assert select(m,22,Config())['reason']=='zero_average_drop'

def test_primary_level_stop_and_delayed_first_entry():
 f=select(market(),22,Config());assert f['reason']=='eligible' and f['dip_level']==99 and f['stop_price']==95
 assert f['signal_slot']==4 and f['entry_slot']==6 and f['sizing_price']==98.9

def test_level_at_cent_not_rounded_too_far():
 assert select(market(),22,Config(multiplier=.4))['dip_level']==99.6

def test_equal_level_insufficient():
 m=market();m.arrays['close'][-1,:]=99.;m.arrays['low'][-1,:]=98.5;assert select(m,22,Config())['reason']=='no_signal'

def test_first_candidate_geometry_consumes_day():
 m=market();bar(m,4,close=94.,low=93.);bar(m,9,close=98.8)
 f=select(m,22,Config());assert f['reason']=='invalid_geometry' and f['decision_slot']==5

def test_missing_scan_blocks_later_candidate():
 m=market();bar(m,1,volume=np.nan);assert select(m,22,Config())['reason']=='unknown_scan'

def test_conflict_global_rejected():
 m=market();m.quality.loc[22,'reason']='conflicting_duplicates';assert select(m,22,Config())['reason']=='unknown_source'

def test_half_current_known_inactivity():
 m=market();m.lengths[-1]=210;assert select(m,22,Config())['reason']=='half_session'

def test_red_filter_is_prior_open_close_not_close_close():
 m=market();assert select(m,22,Config(red_filter=True))['reason']=='eligible'
 m.arrays['close'][-2,389]=101.;assert select(m,22,Config(red_filter=True))['reason']=='red_filtered'

def test_dollar_raw_series_without_dividend_adjustment():
 m=market();m.arrays['open'][10,0]=99.;assert history(m,Config())[-1]['average_drop']==pytest.approx(20/21)

def test_other_grids_and_end_cutoff():
 m=market();assert select(m,22,Config(bar_minutes=1))['entry_slot']==6
 m.arrays['close'][-1,:]=100.;bar(m,154,close=98.9,low=98.5)
 assert select(m,22,Config())['reason']=='eligible' and select(m,22,Config(end_minute=150))['reason']=='no_signal'

def test_causal_quantity_and_roundtrip_fees():
 t=run().trades.iloc[0];assert t.quantity==1000 and t.net_pnl==pytest.approx(973) and t.commission==7 and t.friction_cost==20 and t.borrow_fee==0
def test_small_account_min_commission():
 t=run(c=Config(initial_capital=1000)).trades.iloc[0];assert t.quantity==10 and t.commission==.7 and t.net_pnl==pytest.approx(9.1)
def test_risk_sizing():
 f=feature();f['stop_price']=98.;assert run(f=f).trades.iloc[0].quantity==500
def test_entry_gap_not_resized():
 m=market();bar(m,106,open=110.,close=110.,high=111.,low=109.);t=run(m).trades.iloc[0];assert t.quantity==1000 and t.entry_leverage>1
def test_entry_below_stop_pays_all_costs():
 m=market();bar(m,106,open=98.);t=run(m).trades.iloc[0];assert t.exit_reason=='entry_marketable_stop' and t.net_pnl==pytest.approx(-27)
def test_intrabar_stop_and_terminal_extremes():
 m=market();m.arrays['low'][-1,106:108]=99.5;bar(m,108,high=1000000.,low=98.);t=run(m).trades.iloc[0]
 assert t.exit_reference==99 and t.exit_resolution=='intrabar_minute_unknown' and t.mfe_price_usd==pytest.approx(990) and t.mae_price_usd==pytest.approx(-1020)
def test_gap_stop_before_missing_wick():
 m=market();bar(m,108,open=98.,high=np.nan,low=np.nan);assert run(m,c=Config(quality='resolved_prefix')).trades.iloc[0].exit_reason=='stop_gap'
def test_no_stop_keeps_sizing_but_runs_to_eod():
 m=market();bar(m,108,low=1.);t=run(m,c=Config(stop_enabled=False)).trades.iloc[0];assert t.quantity==1000 and t.exit_slot==389
def test_missing_active_preserves_known_entry_costs():
 m=market();bar(m,108,volume=np.nan);r=run(m,c=Config(quality='resolved_prefix'));assert r.trades.empty and len(r.unresolved)==1
 assert r.daily.observed_return.isna().all() and r.unresolved.iloc[0].known_entry_commission==3.5 and r.unresolved.iloc[0].known_entry_friction==10
def test_missing_entry_no_fill():
 m=market();bar(m,106,open=np.nan);assert run(m,c=Config(quality='resolved_prefix')).unresolved.iloc[0].known_entry_commission==0
def test_unheld_gap_prefix():
 m=market();bar(m,105,volume=np.nan);m.valid[-1]=False;assert run(m).trades.empty and len(run(m,c=Config(quality='resolved_prefix')).trades)==1
def test_last_wicks_not_held():
 m=market();bar(m,389,high=1000000.,low=1.);t=run(m).trades.iloc[0];assert t.exit_reason=='eod_open' and t.mfe_price_usd==pytest.approx(990)
@pytest.mark.parametrize('kw',[{'window':0},{'multiplier':0},{'multiplier':math.nan},{'bar_minutes':2},{'start_minute':360,'end_minute':350},{'quality':'bad'},{'slippage':-1},{'initial_capital':0}])
def test_invalid_config(kw):
 with pytest.raises(ValueError):Config(**kw)


def test_rebound_above_threshold_still_market_entry():
 m=market();f=select(m,22,Config());bar(m,f['entry_slot'],open=105.,high=106.,low=104.,close=105.)
 t=simulate(m,[f],Config(),f['date'],f['date']).trades.iloc[0];assert t.entry_reference==105 and t.entry_reference>t.dip_level

def test_independent_scalar_parity_on_synthetic_path():
 from audit.independent import features,replay
 m=market();c=Config();fs=prepare(m,c);other=features(m,c)
 for a,b in zip(fs,other):
  for k in a:
   if isinstance(a[k],float):assert a[k]==pytest.approx(b[k])
   else:assert a[k]==b[k]
 r=simulate(m,fs,c,fs[-1]['date'],fs[-1]['date']);d,t,u,dd,usd=replay(m,other,c,fs[-1]['date'],fs[-1]['date'])
 assert len(t)==len(r.trades)==1 and t[0]['net_pnl']==pytest.approx(r.trades.iloc[0].net_pnl) and dd==pytest.approx(r.observed_close_drawdown_pct)

def test_stopless_quantity_does_not_use_future_gap():
 m=market();f=select(m,22,Config());one=simulate(m,[f],Config(stop_enabled=False),f['date'],f['date']).trades.iloc[0]
 bar(m,f['entry_slot'],open=500.,high=501.,low=499.,close=500.)
 two=simulate(m,[f],Config(stop_enabled=False),f['date'],f['date']).trades.iloc[0];assert one.quantity==two.quantity and two.entry_leverage>1

def test_invalid_adr_configuration():
 with pytest.raises(ValueError):Config(adr_days=0)


def test_red2_does_not_require_older_unknown_streak():
 m=market(24);m.valid[0]=False
 assert history(m,Config(red_filter=True))[-1]['previous_red_count']==2
 assert select(m,23,Config(red_filter=True))['reason']=='eligible'

def test_exact_adr_fourteen_day_boundary():
 m=market();m.arrays['low'][7,:]=1.;m.arrays['low'][8,:]=97.
 assert history(m,Config())[-1]['adr']==pytest.approx(57/14)

@pytest.mark.parametrize('problem',['gap','unknown'])
def test_scalar_parity_stop_gap_and_unresolved(problem):
 from audit.independent import features,replay
 m=market();c=Config(quality='resolved_prefix')
 if problem=='gap':bar(m,10,open=94.,high=95.,low=93.,close=94.)
 else:bar(m,10,volume=np.nan);m.valid[-1]=False
 fs=prepare(m,c);other=features(m,c);start=end=fs[-1]['date'];r=simulate(m,fs,c,start,end);d,t,u,dd,usd=replay(m,other,c,start,end)
 assert len(t)==len(r.trades) and len(u)==len(r.unresolved) and dd==pytest.approx(r.observed_close_drawdown_pct)
 if t:assert t[0]['net_pnl']==pytest.approx(r.trades.iloc[0].net_pnl) and t[0]['exit_reason']==r.trades.iloc[0].exit_reason
 if u:assert u[0]['known_entry_friction']==pytest.approx(r.unresolved.iloc[0].known_entry_friction)
