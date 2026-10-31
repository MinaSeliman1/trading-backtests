from pathlib import Path
from types import SimpleNamespace
import math,sys
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from variation.engine import Config,morning,prepare,signal,execute,simulate,Unresolved

def market(days=8):
 dates=pd.bdate_range(end='2024-02-06',periods=days)
 a={k:np.full((days,390),v,dtype=float) for k,v in dict(open=100.,high=100.5,low=99.5,close=100.,volume=1000.).items()}
 for i in range(days-1):
  returns=np.array([.0002+.00001*i,-.00015+.00001*i,-.0001+.00001*i,-.00015+.00001*i]*15);a['close'][i,:60]=100*np.exp(np.cumsum(returns));a['high'][i,:60]=np.maximum(100.5,a['close'][i,:60]);a['low'][i,:60]=np.minimum(99.5,a['close'][i,:60])
 a['open'][-1,0]=99.;a['close'][-1,:60]=99*np.exp(math.log(100/99)*(np.arange(60)+1)/60);a['close'][-1,59]=100.;a['low'][-1,:60]=98.5
 for k,v in dict(open=101.,close=101.,high=101.5,low=100.5).items():a[k][-1,389]=v
 return SimpleNamespace(symbol='SPY',dates=dates,arrays=a,lengths=np.full(days,390),valid=np.ones(days,bool),quality=pd.DataFrame({'session_open':[str(d.date())+' 09:30:00-05:00' for d in dates],'reason':['']*days}))

def cfg(**k):return Config(min_history=3,**k)
def f(m,c=None):return prepare(m,c or cfg())[-1]
def s(m,c=None):return signal(f(m,c),c or cfg())
def run(m,c=None):
 c=c or cfg();ff=f(m,c);return simulate(m,[ff],c,ff['date'],ff['date'])
def bar(m,j,**values):
 for k,v in values.items():m.arrays[k][-1,j]=v
 if 'open' in values or 'close' in values:
  
  if 'high' not in values:m.arrays['high'][-1,j]=max(m.arrays['open'][-1,j],m.arrays['close'][-1,j])+.5
  if 'low' not in values:m.arrays['low'][-1,j]=min(m.arrays['open'][-1,j],m.arrays['close'][-1,j])-.5

def test_two_minute_variation_without_overnight():
 m=market();m.arrays['open'][-1,0]=100.;m.arrays['close'][-1,:4]=100.;m.arrays['high'][-1,:4]=102.;m.arrays['low'][-1,:4]=99.;m.arrays['close'][-1,1]=101.
 x=morning(m,7,cfg(observation_minutes=4));assert x['log_return']==0 and x['variation']==pytest.approx(math.sqrt(2)*math.log(1.01)) and x['score']==0
 m.arrays['close'][-2,389]=10000.;assert morning(m,7,cfg(observation_minutes=4))==x

def test_smooth_ratio_has_no_annualization():assert f(market())['score']==pytest.approx(math.sqrt(30))
def test_current_and_future_data_not_in_threshold():
 m=market();a=f(m);m.arrays['close'][-1,61:]=10000.;assert f(m)==a
 m.arrays['close'][-1,:60]=99.;m.arrays['low'][-1,:60]=98.;b=f(m);assert b['threshold']==a['threshold'] and b['training_count']==7

def test_minimum252_previous_eligible_scores():
 fs=prepare(market(254),Config());assert fs[251]['reason']=='warmup' and fs[251]['training_count']==251
 assert fs[252]['reason']=='ready' and fs[252]['training_count']==252

def test_half_days_and_missing_mornings_not_imputed():
 m=market();m.lengths[1]=210;m.arrays['low'][2,5]=np.nan;fs=prepare(m,cfg());assert fs[-1]['training_count']==5 and fs[1]['reason']=='half_session' and fs[2]['reason']=='unknown_morning'

def test_unsampled_invalid_minute_invalidates_signal():
 m=market();bar(m,0,volume=np.nan);assert f(m)['reason']=='unknown_morning'

def test_zero_variation_known_no_trade_and_not_in_pool():
 m=market();m.arrays['close'][0,:60]=100.;assert f(m)['training_count']==6
 for k in ['open','close']:m.arrays[k][-1,:60]=100.
 assert f(m)['reason']=='zero_variation' and s(m)['reason']=='zero_variation'

def test_historical_afternoon_gap_does_not_erase_known_morning():
 m=market();a=f(m);m.valid[1]=False;m.quality.loc[1,'reason']='missing_minutes';m.arrays['low'][1,200]=np.nan
 assert f(m)['threshold']==a['threshold'] and f(m)['training_count']==7

def test_conflicting_source_flag_rejected():
 m=market();m.quality.loc[7,'reason']='conflicting_duplicates';assert f(m)['reason']=='unknown_morning'

def test_linear_quantile_hand_computed():
 m=market(4)
 for i,(a,b) in enumerate([(.01,0),(.01,.01),(.01,-.01),(.01,.01)]):
  m.arrays['open'][i,0]=100.;m.arrays['close'][i,:4]=100.;m.arrays['close'][i,1]=100*math.exp(a);m.arrays['close'][i,3]=100*math.exp(a+b);m.arrays['high'][i,:4]=104.;m.arrays['low'][i,:4]=99.
 ff=f(m,cfg(observation_minutes=4));assert ff['threshold']==pytest.approx(1.331370849898476) and ff['training_count']==3

def test_threshold_strict_without_extra_sign_filter():
 ff=f(market());ff['selection_value']=ff['threshold'];assert signal(ff,cfg())['reason']=='no_signal'
 ff['threshold']=-1.;ff['selection_value']=-.5;assert signal(ff,cfg())['reason']=='eligible'

def test_raw_and_always_controls_are_explicit():
 raw=f(market(),cfg(metric='return'));assert raw['selection_value']==raw['log_return']
 ff=f(market());ff['selection_value']=-100.;assert signal(ff,cfg(metric='always'))['reason']=='eligible'

@pytest.mark.parametrize('sample',[1,2,5])
def test_sampling_grid_ends_at_same_close(sample):
 ff=f(market(),cfg(sampling_minutes=sample));assert ff['sizing_price']==100 and ff['signal_slot']==59

def test_rolling_pool_uses_last_min_history():
 ff=f(market(),cfg(history_mode='rolling'));assert ff['training_count']==3 and ff['total_previous_eligible']==7

def test_causal_quantity_and_delayed_fill():
 m=market();t=run(m).trades.iloc[0];assert t.quantity==1000 and t.entry_slot==61 and t.signal_slot==59 and t.exit_slot==389
 bar(m,61,open=110.);z=run(m).trades.iloc[0];assert z.quantity==1000 and z.entry_leverage>1

def test_roundtrip_fees_once_no_borrow():
 t=run(market()).trades.iloc[0];assert t.price_move_pnl==1000 and t.friction_cost==20 and t.commission==7 and t.borrow_fee==0 and t.net_pnl==pytest.approx(973.)

def test_minimum_commission_both_sides():
 t=run(market(),cfg(initial_capital=1000)).trades.iloc[0];assert t.quantity==10 and t.commission==.7 and t.friction_cost==pytest.approx(.2) and t.net_pnl==pytest.approx(9.1)

def test_no_hidden_stop():
 m=market();bar(m,80,low=1.);assert run(m).trades.iloc[0].exit_slot==389

def test_open_exit_does_not_hold_last_wick():
 m=market();bar(m,389,high=1000000.,low=1.);t=run(m).trades.iloc[0];assert t.mfe_price_usd==pytest.approx(980.) and t.exit_reference==101

def test_close_exit_holds_last_minute():
 m=market();bar(m,389,close=102.,low=99.);t=run(m,cfg(exit_kind='close')).trades.iloc[0]
 assert t.exit_reference==102 and t.mae_price_usd==pytest.approx(-1010.) and t.holding_minutes==329

def test_unheld_minute_gap_allowed_in_prefix():
 m=market();bar(m,60,volume=np.nan);m.valid[-1]=False;m.quality.loc[7,'reason']='missing_minutes'
 assert run(m).trades.empty and len(run(m,cfg(quality='resolved_prefix')).trades)==1

def test_active_gap_omits_trade_keeps_known_costs():
 m=market();bar(m,80,volume=np.nan);r=run(m,cfg(quality='resolved_prefix'))
 assert r.trades.empty and len(r.unresolved)==1 and r.daily.observed_return.isna().all()
 assert r.unresolved.iloc[0].known_entry_commission==3.5 and r.unresolved.iloc[0].known_entry_friction==10

def test_unknown_entry_not_reported_filled():
 m=market();bar(m,61,open=np.nan);r=run(m,cfg(quality='resolved_prefix'));assert r.trades.empty and r.unresolved.iloc[0].known_entry_commission==0

def test_noon_entry_after_decision():
 t=run(market(),cfg(observation_minutes=150,metric='always')).trades.iloc[0];assert t.signal_slot==149 and t.entry_slot==151

def test_current_half_session_known_no_trade():
 m=market();m.lengths[-1]=210;r=run(m);assert r.trades.empty and r.daily.eligibility.iloc[0]=='half_session' and not r.daily.conditionally_excluded.iloc[0]

@pytest.mark.parametrize('kw',[{'sampling_minutes':3},{'observation_minutes':3},{'min_history':1},{'quantile':1.},{'slippage':-1},{'metric':'bad'},{'quality':'bad'},{'initial_capital':0},{'history_mode':'bad'},{'exit_kind':'bad'}])
def test_invalid_config(kw):
 with pytest.raises(ValueError):Config(**kw)


def test_exit_fill_friction_is_in_adverse_excursion():
 m=market();bar(m,389,open=99.);t=run(m).trades.iloc[0]
 assert t.mae_price_usd==pytest.approx(-1020.)


@pytest.mark.parametrize('reason',['invalid_ohlcv','missing_minutes|invalid_ohlcv'])
def test_afternoon_invalid_flag_does_not_erase_morning(reason):
 m=market();prior=f(m);m.arrays['volume'][1,200]=np.nan;m.valid[1]=False;m.quality.loc[1,'reason']=reason
 assert f(m)['training_count']==7 and f(m)['threshold']==prior['threshold']
