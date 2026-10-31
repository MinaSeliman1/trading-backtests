from pathlib import Path
from types import SimpleNamespace
import sys,math
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bb.engine import Config,prepare,select,trace,simulate,Unresolved

def market():
 a={k:np.full((2,390),v,float) for k,v in dict(open=100.,high=100.5,low=99.5,close=100.,volume=1000.).items()}
 for k,v in dict(open=101.,high=101.5,low=100.5,close=101.).items():a[k][-1,389]=v
 return SimpleNamespace(symbol='SPY',dates=pd.date_range('2024-02-05',periods=2),arrays=a,lengths=np.array([390,390]),valid=np.array([True,True]),quality=pd.DataFrame({'session_open':['2024-02-05 09:30:00-05:00','2024-02-06 09:30:00-05:00'],'reason':['','']}))
def path():
 m=market()
 for b,price in enumerate([100.,101.,100.,95.,97.]):
  for k,v in dict(open=price,close=price,high=price+.2,low=price-.2).items():m.arrays[k][-1,b*5:(b+1)*5]=v
 return m
def small(**kw):return Config(lookback=3,band=1.,start_minute=20,end_minute=60,**kw)
def feature():
 return dict(index=1,date='2024-02-06',session_minutes=390,reason='eligible',bar_index=20,decision_slot=105,signal_slot=104,entry_slot=106,
 sizing_price=100.,stop_price=99.,target_price=102.,middle=102.,lower=99.,previous_lower=99.2,previous_close=98.)
def run(m=None,c=None,f=None):
 m=m or market();f=f or feature();return simulate(m,[f],c or Config(),f['date'],f['date'])
def bar(m,j,**kw):
 for k,v in kw.items():m.arrays[k][-1,j]=v

def test_reentry_bands_population_and_first_selection():
 f=select(path(),1,small())
 assert f['reason']=='eligible' and f['signal_slot']==24 and f['entry_slot']==26
 assert f['middle']==pytest.approx(292/3) and f['lower']==pytest.approx(292/3-np.std([100,95,97],ddof=0))
 assert f['target_price']==97.33 and f['stop_price']==94.79
def test_no_overnight_carry():
 m=path();a=select(m,1,small());m.arrays['close'][0,:]=100000;assert select(m,1,small())==a
def test_future_does_not_change_first_signal():
 m=path();a=select(m,1,small())
 for k in ('open','close','high','low'):m.arrays[k][-1,30:]=1000.
 assert select(m,1,small())==a
def test_bands_reset_each_session_and_flat_no_signal():
 m=market();assert select(m,1,Config())['reason']=='no_signal'
def test_outside_touch_is_separate():
 m=path();f=select(m,1,small(entry_rule='outside_touch'));assert f['signal_slot']==19
def test_target_one_r_fixed_before_fill():
 f=select(path(),1,small(target_kind='one_r'));assert f['target_price']==99.21
def test_missing_scan_does_not_skip_unknown_first_chance():
 m=path();bar(m,2,volume=np.nan);assert select(m,1,small())['reason']=='unknown_scan'
def test_later_local_invalid_does_not_erase_signal():
 m=path();a=select(m,1,small());bar(m,250,volume=np.nan);m.valid[-1]=False;m.quality.loc[1,'reason']='missing_minutes|invalid_ohlcv'
 assert select(m,1,small())==a
def test_conflict_blocks_scan():
 m=path();m.quality.loc[1,'reason']='conflicting_duplicates';assert select(m,1,small())['reason']=='unknown_source'
def test_half_session_known_inactivity():
 m=path();m.lengths[-1]=210;assert select(m,1,small())['reason']=='half_session'
def test_main_causal_quantity_fees_and_timing():
 t=run().trades.iloc[0];assert t.quantity==1000 and t.entry_slot==106 and t.signal_slot==104
 assert t.net_pnl==pytest.approx(973) and t.commission==7 and t.friction_cost==20 and t.borrow_fee==0
def test_minimum_commission():
 t=run(c=Config(initial_capital=1000)).trades.iloc[0];assert t.quantity==10 and t.commission==.7 and t.net_pnl==pytest.approx(9.1)
def test_risk_cap_before_fill():
 f=feature();f['stop_price']=98.;t=run(f=f).trades.iloc[0];assert t.quantity==500
def test_entry_gap_never_resizes():
 m=market();bar(m,106,open=110.);t=run(m).trades.iloc[0];assert t.quantity==1000 and t.entry_leverage>1 and t.exit_slot==106 and t.exit_reason=='entry_marketable_target'
def test_entry_below_stop_costs_roundtrip():
 m=market();bar(m,106,open=98.);t=run(m).trades.iloc[0];assert t.exit_slot==106 and t.exit_reference==98 and t.net_pnl==pytest.approx(-27)
def test_both_touched_stop_first():
 m=market();bar(m,108,high=103.,low=98.);t=run(m).trades.iloc[0]
 assert t.exit_reference==99 and t.ambiguous_bar and t.exit_reason=='stop_intrabar'
def test_target_single_touch():
 m=market();bar(m,108,high=103.);t=run(m).trades.iloc[0];assert t.exit_reference==102 and t.exit_resolution=='intrabar_minute_unknown'
def test_gap_open_resolves_before_missing_wick():
 m=market();bar(m,108,open=103.,high=np.nan,low=np.nan);t=run(m,c=Config(quality='resolved_prefix')).trades.iloc[0];assert t.exit_reason=='target_gap' and t.exit_reference==103
def test_missing_active_is_unknown_and_entry_costs_saved():
 m=market();bar(m,108,volume=np.nan);r=run(m,c=Config(quality='resolved_prefix'))
 assert r.trades.empty and len(r.unresolved)==1 and r.daily.observed_return.isna().all()
 assert r.unresolved.iloc[0].known_entry_commission==3.5 and r.unresolved.iloc[0].known_entry_friction==10
def test_missing_entry_no_fictional_fill():
 m=market();bar(m,106,open=np.nan);r=run(m,c=Config(quality='resolved_prefix'));assert r.unresolved.iloc[0].known_entry_commission==0
def test_unheld_minute_gap_prefix_only():
 m=market();bar(m,105,volume=np.nan);m.valid[-1]=False
 assert run(m).trades.empty and len(run(m,c=Config(quality='resolved_prefix')).trades)==1
def test_eod_open_excludes_last_wicks():
 m=market();bar(m,389,high=1e6,low=1.);t=run(m).trades.iloc[0]
 assert t.exit_reason=='eod_open' and t.exit_reference==101 and t.mfe_price_usd==pytest.approx(980)
def test_terminal_intrabar_wick_excluded_from_mae_mfe():
 m=market();bar(m,108,high=1e6,low=98.);t=run(m).trades.iloc[0];assert t.mfe_price_usd==pytest.approx(490) and t.mae_price_usd==pytest.approx(-1020)
def test_delay_zero_explicit():
 f=select(path(),1,small(entry_delay=0));assert f['entry_slot']==25
@pytest.mark.parametrize('kw',[{'lookback':1},{'bar_minutes':3},{'band':0},{'band':math.nan},{'entry_rule':'bad'},{'target_kind':'bad'},{'start_minute':100,'end_minute':90},{'entry_delay':2},{'quality':'bad'},{'slippage':-1},{'initial_capital':0}])
def test_invalid_config(kw):
 with pytest.raises(ValueError):Config(**kw)


def test_mean_cent_boundary_has_no_binary_floor_error():
 m=path()
 for k,v in dict(open=96.03,close=96.03,high=96.23,low=95.83).items():m.arrays[k][-1,20:25]=v
 assert select(m,1,small())['target_price']==97.01
