from pathlib import Path
from types import SimpleNamespace
import sys,math
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lunch.engine import Config,context,prepare,select,trace,simulate,Unresolved

def market(days=3):
 a={k:np.full((days,390),v,float) for k,v in dict(open=100.,high=101.,low=99.5,close=100.,volume=1000.).items()}
 a['high'][:,0]=102.;a['low'][:,0]=98.
 a['high'][:,120:180]=100.4;a['low'][:,120:180]=99.6
 for k,v in dict(open=100.5,high=100.8,low=100.3,close=100.5).items():a[k][:,180:389]=v
 for k,v in dict(open=100.,high=100.2,low=99.9,close=100.).items():a[k][:,209]=v
 a['volume'][:,210:215]=2000.
 for k,v in dict(open=101.,high=101.5,low=100.5,close=101.).items():a[k][:,389]=v
 dates=pd.bdate_range(end='2024-02-06',periods=days)
 return SimpleNamespace(symbol='SPY',dates=dates,arrays=a,lengths=np.full(days,390),valid=np.ones(days,bool),
  quality=pd.DataFrame({'session_open':[str(d.date())+' 09:30:00-05:00' for d in dates],'reason':['']*days}))

def feature():
 return dict(index=2,date='2024-02-06',session_minutes=390,reason='eligible',morning_high=102.,morning_low=98.,morning_range=4.,lunch_high=100.4,lunch_low=99.6,lunch_range=.8,
 compression_ratio=.2,lunch_volume_mean=1000.,morning_return=0.,breakout_level=100.4,stop_price=99.,bar_index=20,decision_slot=105,signal_slot=104,entry_slot=106,sizing_price=100.,volume_ratio=2.)

def run(m=None,c=None,f=None):
 m=m or market();f=f or feature();return simulate(m,[f],c or Config(),f['date'],f['date'])

def bar(m,j,**kw):
 for k,v in kw.items():m.arrays[k][-1,j]=v

def test_first_fresh_afternoon_cross_after_compression():
 f=select(market(),2,Config());assert f['reason']=='eligible' and f['entry_slot']==216 and f['stop_price']==100. and f['volume_ratio']==2

def test_fixed_context_and_decimal_compression_boundary():
 m=market();h=context(m,2,Config());assert h['morning_range']==4 and h['lunch_range']==.8 and h['compression_ratio']==.2
 assert select(m,2,Config(max_compression=.2))['reason']=='not_compressed'

def test_future_prices_and_validity_cannot_change_earlier_selection():
 m=market();f=select(m,2,Config())
 for k in ('open','high','low','close'):m.arrays[k][-1,250:]=100000.
 m.valid[-1]=False;m.quality.loc[2,'reason']='missing_minutes|invalid_ohlcv'
 assert select(m,2,Config())==f

def test_post_lunch_extremes_do_not_change_levels():
 m=market();h=context(m,2,Config());bar(m,200,high=10000.,low=.01)
 assert context(m,2,Config())==h and select(m,2,Config())['reason']=='eligible'

def test_already_above_at_1300_is_not_fresh_cross():
 m=market();bar(m,209,open=100.5,high=100.8,low=100.3,close=100.5)
 assert select(m,2,Config())['reason']=='no_signal'

def test_equal_close_is_not_breakout():
 m=market();m.arrays['close'][-1,210:301]=100.4
 assert select(m,2,Config())['reason']=='no_signal'

def test_first_cross_volume_failure_consumes_day():
 m=market();m.arrays['volume'][-1,210:215]=1000.;bar(m,219,open=100.,high=100.2,low=99.9,close=100.)
 m.arrays['volume'][-1,220:225]=10000.
 f=select(m,2,Config());assert f['reason']=='volume_filtered' and f['entry_slot']==216
 assert select(m,2,Config(volume_filter=False))['reason']=='eligible'

def test_volume_strict_equality_and_higher_multiple():
 m=market();assert select(m,2,Config(volume_multiple=2.))['reason']=='volume_filtered'
 assert select(m,2,Config(volume_multiple=1.5))['reason']=='eligible'

def test_zero_lunch_volume_allowed_only_with_filter_off():
 m=market();m.arrays['volume'][-1,120:180]=0
 assert select(m,2,Config())['reason']=='zero_lunch_volume'
 f=select(m,2,Config(volume_filter=False));assert f['reason']=='eligible' and f['volume_ratio'] is None

def test_extended_lunch_changes_volume_units_and_levels():
 m=market();f=select(m,2,Config(lunch_end=210,max_compression=.5))
 assert f['lunch_high']==100.8 and f['lunch_volume_mean']==1000 and f['reason']=='no_signal'

def test_grids_use_volume_per_minute_and_after_1300():
 m=market();f=select(m,2,Config(bar_minutes=1));assert f['decision_slot']==211 and f['entry_slot']==212 and f['volume_ratio']==2
 m.arrays['volume'][-1,210:225]=2000.;f=select(m,2,Config(bar_minutes=15));assert f['decision_slot']==225 and f['entry_slot']==226 and f['volume_ratio']==2

def test_stop_low_alternative_and_cent_rounding():
 m=market();assert select(m,2,Config(stop_kind='low'))['stop_price']==99.6
 m.arrays['high'][-1,120:180]=100.401
 f=select(m,2,Config());assert f['breakout_level']==100.41 and f['stop_price']==100.

def test_morning_up_uses_pre_lunch_not_afternoon():
 m=market();assert select(m,2,Config(morning_up=True))['reason']=='morning_filtered'
 bar(m,119,close=100.1);assert select(m,2,Config(morning_up=True))['reason']=='eligible'

def test_missing_context_is_unknown():
 m=market();bar(m,130,volume=np.nan);assert select(m,2,Config())['reason']=='unknown_context'

def test_missing_waiting_period_blocks_scan():
 m=market();bar(m,190,volume=np.nan);assert select(m,2,Config())['reason']=='unknown_scan'

def test_global_conflicts_and_planned_half_session():
 m=market();m.quality.loc[2,'reason']='conflicting_duplicates';assert select(m,2,Config())['reason']=='unknown_source'
 m.lengths[-1]=210;assert select(m,2,Config())['reason']=='half_session'

def test_zero_ranges_known_inactivity():
 m=market()
 for k in ('open','high','low','close'):m.arrays[k][-1,:120]=100.
 assert select(m,2,Config())['reason']=='zero_morning_range'

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
def test_missing_active_preserves_known_entry_costs():
 m=market();bar(m,108,volume=np.nan);r=run(m,c=Config(quality='resolved_prefix'));assert r.trades.empty and len(r.unresolved)==1
 assert r.daily.observed_return.isna().all() and r.unresolved.iloc[0].known_entry_commission==3.5 and r.unresolved.iloc[0].known_entry_friction==10
def test_missing_entry_no_fill():
 m=market();bar(m,106,open=np.nan);assert run(m,c=Config(quality='resolved_prefix')).unresolved.iloc[0].known_entry_commission==0
def test_unheld_gap_prefix():
 m=market();bar(m,105,volume=np.nan);m.valid[-1]=False;assert run(m).trades.empty and len(run(m,c=Config(quality='resolved_prefix')).trades)==1
def test_last_wicks_not_held():
 m=market();bar(m,389,high=1000000.,low=1.);t=run(m).trades.iloc[0];assert t.exit_reason=='eod_open' and t.mfe_price_usd==pytest.approx(990)

@pytest.mark.parametrize('kw',[{'max_compression':0},{'lunch_end':170},{'bar_minutes':2},{'start_minute':300,'end_minute':300},{'volume_multiple':0},{'stop_kind':'x'},{'quality':'x'},{'slippage':-1},{'initial_capital':0}])
def test_invalid_config(kw):
 with pytest.raises(ValueError):Config(**kw)

@pytest.mark.parametrize('problem',['normal','gap','unknown'])
def test_independent_scalar_parity_and_compounding(problem):
 from audit.independent import features,replay
 m=market();c=Config(quality='resolved_prefix')
 if problem=='gap':bar(m,218,open=99.,high=100.,low=98.,close=99.)
 elif problem=='unknown':bar(m,218,volume=np.nan);m.valid[-1]=False
 fs=prepare(m,c);other=features(m,c)
 for aa,bb in zip(fs,other):
  for k in aa:
   if isinstance(aa[k],float):assert aa[k]==pytest.approx(bb[k])
   else:assert aa[k]==bb[k]
 start,end=fs[0]['date'],fs[-1]['date'];r=simulate(m,fs,c,start,end);d,t,u,dd,usd=replay(m,other,c,start,end)
 assert len(t)==len(r.trades) and len(u)==len(r.unresolved) and dd==pytest.approx(r.observed_close_drawdown_pct)
 assert [x['net_pnl'] for x in t]==pytest.approx(r.trades.net_pnl.tolist())
 assert d[-1]['equity']==pytest.approx(r.daily.iloc[-1].equity)

def test_matrix_exactly_fourteen_variants():
 import importlib.util
 spec=importlib.util.spec_from_file_location("lunch_study_matrix_test",Path(__file__).resolve().parents[1]/"scripts/run_study.py")
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);specifications=module.specifications
 from dataclasses import asdict
 specs=specifications();assert len(specs)==14 and len({n for n,c in specs})==14
 assert all(sum(v!=asdict(Config())[k] for k,v in asdict(c).items())==1 for n,c in specs[1:])


def test_cutoff_inclusive_and_no_later_candidate():
 m=market();m.arrays['close'][-1,180:301]=100.;m.arrays['low'][-1,180:301]=99.9
 bar(m,299,close=100.5);m.arrays['volume'][-1,295:300]=2000.
 assert select(m,2,Config())['decision_slot']==300
 bar(m,299,close=100.);assert select(m,2,Config())['reason']=='no_signal'

def test_zero_lunch_range_known_inactivity():
 m=market()
 for k in ('open','high','low','close'):m.arrays[k][-1,120:180]=100.
 assert select(m,2,Config())['reason']=='zero_lunch_range'

def test_actual_signal_quantity_not_resized_at_gap():
 m=market();f=select(m,2,Config());one=simulate(m,[f],Config(),f['date'],f['date']).trades.iloc[0]
 bar(m,216,open=110.,high=111.,low=109.,close=110.)
 two=simulate(m,[f],Config(),f['date'],f['date']).trades.iloc[0]
 assert one.quantity==two.quantity and two.entry_leverage>1

def test_actual_signal_unknown_delay_is_not_held():
 m=market();f=select(m,2,Config());bar(m,215,volume=np.nan);m.valid[-1]=False
 assert select(m,2,Config())==f
 assert len(simulate(m,[f],Config(quality='resolved_prefix'),f['date'],f['date']).trades)==1

@pytest.mark.parametrize('problem',['normal'])
def test_half_session_does_not_require_afternoon_data(problem):
 m=market();m.lengths[-1]=210
 for k in m.arrays:m.arrays[k][-1,210:]=np.nan
 assert select(m,2,Config())['reason']=='half_session'


def test_scalar_replay_accepts_exported_configuration_record():
 from dataclasses import asdict
 from audit.independent import features,replay
 m=market();c=SimpleNamespace(**asdict(Config()));fs=features(m,c)
 days,trades,unknown,dd,usd=replay(m,fs,c,fs[0]['date'],fs[-1]['date'])
 assert len(trades)==3 and not unknown


def additional_module():
 import importlib.util
 spec=importlib.util.spec_from_file_location('lunch_extra_test',Path(__file__).resolve().parents[1]/'scripts/additional_checks.py')
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

@pytest.mark.parametrize('returns,pnl,wr,pf',[( [0.,0.],[],None,None),([.01,.02],[10.,20.],100.,None),([.01,-.01],[10.,-5.],50.,2.)])
def test_independent_stats_legitimate_empty_or_no_losses(returns,pnl,wr,pf):
 s=additional_module().observed_statistics(returns,pnl);assert s['win_rate_pct']==wr and s['profit_factor']==pf
 if returns==[0.,0.]:assert s['sharpe'] is None

def test_missing_statistics_match_missing_only():
 module=additional_module();module.assert_near(None,float('nan'))
 with pytest.raises(AssertionError):module.assert_near(None,0.)
