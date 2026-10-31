from pathlib import Path
from types import SimpleNamespace
from dataclasses import replace
import sys,copy,math
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from relative.engine import Config,prepare,choose,execute,simulate,Unresolved

def markets(n=390,days=22):
 dates=pd.bdate_range(end='2024-02-06',periods=days);out={}
 for symbol in ['SPY','QQQ']:
  a={k:np.full((days,390),v,dtype=float) for k,v in dict(open=100.,high=101.,low=99.,close=100.,volume=1000.).items()}
  if symbol=='QQQ':
   for i in range(days-1):a['close'][i]=100*np.exp((i-10)*.0001*(np.arange(390)+1)/30)
   a['high']=np.maximum(101.,a['close']);a['low']=np.minimum(99.,a['close'])
  out[symbol]=SimpleNamespace(symbol=symbol,dates=dates.copy(),lengths=np.full(days,n),valid=np.ones(days,bool),arrays=a,quality=pd.DataFrame({'session_open':[str(d.date())+' 09:30:00-05:00' for d in dates]}))
 return out

def bar(m,s,j,**values):
 a=m[s].arrays
 for k,v in values.items():a[k][-1,j]=v
 if 'open' in values or 'close' in values:
  a['high'][-1,j]=max(a['open'][-1,j],a['close'][-1,j])+1
  a['low'][-1,j]=min(a['open'][-1,j],a['close'][-1,j])-1

def feat(m):
 n=int(m['SPY'].lengths[-1]);return dict(index=len(m['SPY'].dates)-1,date=str(m['SPY'].dates[-1].date()),n=n,reason='ready',mean=np.zeros(390),sd=np.full(390,.001),count=np.full(390,20))

def setup(n=390):
 m=markets(n);bar(m,'QQQ',29,close=99.8);bar(m,'QQQ',30,open=99.8,close=99.8)
 return m

def order(m,c=None,capital=100000):return choose(m,feat(m),c or Config(),capital)

def trade(m,c=None):return execute(m,feat(m),order(m,c),c or Config())

def run(m,c=None):
 f=feat(m);return simulate(m,[f],c or Config(),f['date'],f['date'])

def test_prepare_uses_only_past_same_clock_returns():
 m=markets();f=prepare(m,Config())[-1]
 assert f['mean'][29]==pytest.approx(.00005)
 assert f['sd'][29]==pytest.approx(math.sqrt(35)*.0001) and f['count'][29]==20
 m['QQQ'].arrays['close'][-1,:]=10000.;g=prepare(m,Config())[-1]
 np.testing.assert_equal(f['mean'],g['mean']);np.testing.assert_equal(f['sd'],g['sd'])

def test_missing_historical_session_not_skipped():
 m=markets();m['SPY'].valid[-4]=False
 assert prepare(m,Config())[-1]['reason']=='unknown_history'
 assert prepare(m,Config())[19]['reason']=='warmup'

def test_structural_half_session_tail_omitted_but_not_a_gap():
 m=markets();m['QQQ'].lengths[-3]=210;m['SPY'].lengths[-3]=210
 f=prepare(m,Config())[-1];assert f['reason']=='ready' and f['count'][299]==19 and math.isfinite(f['sd'][299])

def test_misaligned_pair_calendar_or_lengths_refused():
 m=markets();m['QQQ'].dates=m['QQQ'].dates+pd.Timedelta(days=1)
 with pytest.raises(ValueError):prepare(m,Config())
 m=markets();m['QQQ'].lengths[-1]=210
 with pytest.raises(ValueError):prepare(m,Config())

def test_negative_spread_buys_qqq_sells_spy_next_open():
 x=order(setup());assert x['sign']==1 and x['signal_slot']==29 and x['entry_slot']==30
 assert x['quantity_qqq']==501 and x['quantity_spy']==500 and x['gross_sizing']<=100000

def test_positive_spread_sells_qqq_buys_spy():
 m=markets();bar(m,'QQQ',29,close=100.25)
 assert order(m)['sign']==-1

def test_threshold_entry_inclusive_stop_exclusive():
 m=markets();bar(m,'QQQ',29,close=100*math.exp(-.002))
 assert order(m)['reason']=='eligible'
 bar(m,'QQQ',29,close=100*math.exp(-.003));assert order(m)['reason']=='no_signal'

def test_no_trade_before_ten_or_after_last_decision():
 m=markets();bar(m,'QQQ',24,close=99.8);bar(m,'QQQ',304,close=99.8)
 assert order(m)['reason']=='no_signal'

def test_zero_variance_is_known_no_trade():
 m=setup();f=feat(m);f['sd'][:]=0
 assert choose(m,f,Config(),100000)['reason']=='no_signal'

def test_future_prices_do_not_change_first_order():
 m=setup();a=order(m);m['QQQ'].arrays['close'][-1,31:]=1.
 assert order(m)==a

def test_filtered_direction_does_not_consume_day():
 m=markets();bar(m,'QQQ',29,close=100.25);bar(m,'QQQ',34,close=99.8)
 assert order(m,Config(direction='long_spread_only'))['signal_slot']==34

def test_cost_filter_can_continue_to_later_candidate():
 m=markets();bar(m,'QQQ',29,close=100*math.exp(-.0000025));f=feat(m);f['sd'][29]=.000001
 # first point meets Z but cannot pay costs; later eligible point still considered.
 bar(m,'QQQ',34,close=99.75)
 assert choose(m,f,Config(cost_gate=True),100000)['signal_slot']==34

def test_delay_variant_does_not_use_future_open_to_resize():
 m=setup();a=order(m,Config(delay=2));assert a['entry_slot']==31 and a['quantity_qqq']==501
 bar(m,'QQQ',31,open=150.);assert order(m,Config(delay=2))==a

def test_mean_exit_uses_next_open_both_legs():
 x=trade(setup());assert x['entry_slot']==30 and x['exit_slot']==32 and x['exit_reason']=='mean_cross'
 assert x['price_move_pnl']==pytest.approx(100.2)

def test_four_order_fees_friction_and_short_borrow_once():
 x=trade(setup());assert x['commission']==pytest.approx(7.007) and x['friction_cost']==pytest.approx(20.02)
 assert x['borrow_fee']==pytest.approx(1.38875) and x['net_pnl']==pytest.approx(71.78425)
 assert sum(t['net_pnl'] for t in x['legs'])==pytest.approx(x['net_pnl'])

def test_small_account_pays_four_minimum_commissions():
 m=setup();o=order(m,capital=1000);x=execute(m,feat(m),o,Config())
 assert x['commission']==1.4 and x['friction_cost']==pytest.approx(.2)
 assert x['net_pnl']==pytest.approx(-.6138875)

def test_close_stop_not_intrabar_and_gap_is_not_favorable_stop_fill():
 m=setup();bar(m,'QQQ',30,low=1.);assert trade(m)['exit_reason']=='mean_cross'
 bar(m,'QQQ',30,close=99.);bar(m,'QQQ',31,open=98.)
 x=trade(m);assert x['exit_reason']=='spread_stop' and x['exit_slot']==31 and x['exit_reference_qqq']==98.

def test_no_reentry_after_first_completed_pair():
 m=setup();bar(m,'QQQ',49,close=99.8);r=run(m)
 assert len(r.trades)==1 and len(r.legs)==2

def test_half_session_eod_uses_last_open_without_last_wick():
 m=setup(210);m['QQQ'].arrays['close'][-1,30:209]=99.8
 bar(m,'QQQ',209,open=99.9,close=np.nan,low=1.)
 x=trade(m);assert x['exit_reason']=='eod_open' and x['exit_slot']==209

def test_last_half_session_signal_cannot_enter_at_or_after_eod():
 m=markets(210);bar(m,'QQQ',209,close=99.8)
 assert order(m)['reason']=='no_signal'

def test_unknown_grid_before_entry_is_not_skipped():
 m=setup();bar(m,'SPY',29,close=np.nan)
 assert order(m)['reason']=='unknown_signal'

def test_unknown_anchor_is_not_known_cash():
 m=setup();bar(m,'SPY',0,open=np.nan)
 assert order(m)['reason']=='unknown_anchor'

def test_unknown_entry_on_one_leg_is_unresolved_pair():
 m=setup();bar(m,'SPY',30,open=np.nan)
 with pytest.raises(Unresolved):trade(m)
 r=run(m);assert r.trades.empty and len(r.unresolved)==1 and r.daily.observed_return.isna().all()

def test_unknown_active_close_on_one_leg_is_unresolved():
 m=setup();bar(m,'SPY',30,close=np.nan)
 with pytest.raises(Unresolved):trade(m)

def test_data_after_resolved_exit_does_not_erase_pair_in_prefix():
 m=setup();bar(m,'QQQ',40,close=np.nan);m['QQQ'].valid[-1]=False
 assert run(m).trades.empty and len(run(m,Config(quality='resolved_prefix')).trades)==1

def test_indicative_risk_is_not_loss_guarantee():
 m=setup();bar(m,'QQQ',30,close=90.);bar(m,'QQQ',31,open=80.)
 x=trade(m);assert x['net_pnl'] < -1000

def test_cost_gate_filters_small_expected_reversion():
 m=setup();f=feat(m);f['sd'][:]=.000001;bar(m,'QQQ',29,close=100*math.exp(-.0000025))
 assert choose(m,f,Config(cost_gate=True),100000)['reason']=='cost_filtered'

@pytest.mark.parametrize('kw',[{'lookback':1},{'entry_z':3.},{'stop_z':0},{'slippage':-1},{'delay':0},{'direction':'bad'},{'quality':'bad'},{'initial_capital':0}])
def test_invalid_config(kw):
 with pytest.raises(ValueError):Config(**kw)


def test_zero_variance_grid_needs_no_current_close():
 m=markets();bar(m,'QQQ',29,close=np.nan);bar(m,'QQQ',34,close=99.8);f=feat(m);f['sd'][29]=0
 assert choose(m,f,Config(),100000)['signal_slot']==34

def test_delay2_exit_beyond_last_open_is_eod_override():
 m=setup(210);m['QQQ'].arrays['close'][-1,30:208]=99.8;bar(m,'QQQ',208,close=100.)
 x=trade(m,Config(delay=2));assert x['exit_slot']==209 and x['exit_reason']=='eod_open'
