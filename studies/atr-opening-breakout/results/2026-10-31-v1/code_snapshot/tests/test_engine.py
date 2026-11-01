from pathlib import Path
from types import SimpleNamespace
import sys,math
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from atr.engine import Config,history,prepare,select,trace,simulate,Unresolved

def market(days=9):
 a={k:np.full((days,390),v,float) for k,v in dict(open=100.,high=101.,low=99.,close=100.,volume=1000.).items()}
 for k,v in dict(open=100.5,high=101.,low=100.2,close=100.75).items():a[k][-1,:5]=v
 a['open'][-1,0]=100.;a['low'][-1,0]=99.8;a['close'][-1,14]=100.75
 for k,v in dict(open=101.,high=101.5,low=100.5,close=101.).items():a[k][-1,389]=v
 # Held path must not accidentally touch the manual stop99.
 a['low'][-1,5:389]=99.5
 dates=pd.bdate_range(end='2024-02-06',periods=days)
 return SimpleNamespace(symbol='SPY',dates=dates,arrays=a,lengths=np.full(days,390),valid=np.ones(days,bool),
  quality=pd.DataFrame({'session_open':[str(d.date())+' 09:30:00-05:00' for d in dates],'reason':['']*days}))
def feature():
 return dict(index=8,date='2024-02-06',session_minutes=390,reason='eligible',atr=2.,previous_close=100.,current_gap=0.,gap_limit=0.,
  opening_price=99.,breakout_level=99.66,stop_price=99.,bar_index=20,decision_slot=105,signal_slot=104,entry_slot=106,sizing_price=100.)
def run(m=None,c=None,f=None):
 m=m or market();f=f or feature();return simulate(m,[f],c or Config(),f['date'],f['date'])
def bar(m,j,**kw):
 for k,v in kw.items():m.arrays[k][-1,j]=v

def test_atr_uses_previous_five_true_ranges_only():
 h=history(market(),Config());assert h[-1]['atr']==2 and h[5]['history_reason']=='warmup' and h[6]['history_reason']=='ready'
def test_true_range_includes_overnight_gap():
 m=market();m.arrays['close'][2,389]=95.;m.arrays['low'][2,389]=94.
 # TR3=max(2,6,4)=6; prior5TR at index8 includeTR3, notTR2.
 assert history(m,Config())[-1]['atr']==pytest.approx(2.8)
def test_current_afternoon_never_enters_atr_or_first_signal():
 m=market();a=select(m,8,Config())
 for k in ('open','high','low','close'):m.arrays[k][-1,100:]=1000.
 assert select(m,8,Config())==a
def test_history_does_not_skip_gap():
 m=market();m.arrays['volume'][5,50]=np.nan;m.valid[5]=False;assert history(m,Config())[-1]['history_reason']=='unknown_history'
def test_current_future_invalid_flag_keeps_early_signal():
 m=market();a=select(m,8,Config());bar(m,250,volume=np.nan);m.valid[-1]=False;m.quality.loc[8,'reason']='missing_minutes|invalid_ohlcv'
 assert select(m,8,Config())==a
def test_past_half_session_uses_real_length():
 m=market();m.lengths[4]=210
 for k in m.arrays:m.arrays[k][4,210:]=np.nan
 assert history(m,Config())[-1]['atr']==2
def test_zero_atr_known_no_trade():
 m=market()
 for k in ('open','high','low','close'):m.arrays[k][:-1,:]=100.
 assert select(m,8,Config())['reason']=='zero_atr'
def test_primary_threshold_stop_and_delayed_first_entry():
 f=select(market(),8,Config());assert f['reason']=='eligible' and f['atr']==2 and f['breakout_level']==100.66
 assert f['signal_slot']==4 and f['entry_slot']==6 and f['stop_price']==100.
def test_level_at_cent_not_rounded_one_cent_too_far():
 f=select(market(),8,Config(multiplier=.4));assert f['breakout_level']==100.8
def test_equal_threshold_is_not_breakout():
 m=market();m.arrays['close'][-1,:]=100.66;f=select(m,8,Config());assert f['reason']=='no_signal'
def test_missing_scan_blocks_later_candidate():
 m=market();bar(m,1,volume=np.nan);assert select(m,8,Config())['reason']=='unknown_scan'
def test_conflict_global_rejected():
 m=market();m.quality.loc[8,'reason']='conflicting_duplicates';assert select(m,8,Config())['reason']=='unknown_source'
def test_half_current_known_inactivity():
 m=market();m.lengths[-1]=210;assert select(m,8,Config())['reason']=='half_session'
def test_gap_record_is_absolute_log_change_not_ratio():
 m=market();bar(m,0,open=98.,low=97.8);h=history(m,Config(gap_record=True))[-1]
 assert h['current_gap']==pytest.approx(abs(math.log(.98))) and h['gap_limit']==0.
 assert select(m,8,Config(gap_record=True))['reason']=='eligible'
def test_equal_record_gap_is_filtered():
 assert select(market(),8,Config(gap_record=True))['reason']=='gap_filtered'
def test_raw_dividend_like_drop_affects_feature_not_adjusted():
 m=market();bar(m,0,open=99.);assert history(m,Config())[-1]['current_gap']==pytest.approx(abs(math.log(.99)))
def test_other_grids_and_end_cutoff():
 m=market();f=select(m,8,Config(bar_minutes=1));assert f['signal_slot']==4 and f['entry_slot']==6
 assert select(m,8,Config(bar_minutes=15))['reason']=='eligible'
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
 m=market();bar(m,108,high=1000000.,low=98.);t=run(m).trades.iloc[0]
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
@pytest.mark.parametrize('kw',[{'atr_days':0},{'multiplier':0},{'multiplier':math.nan},{'bar_minutes':2},{'start_minute':360,'end_minute':350},{'quality':'bad'},{'slippage':-1},{'initial_capital':0}])
def test_invalid_config(kw):
 with pytest.raises(ValueError):Config(**kw)
