import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ema_pullback.engine import Config,prepare,signal,trace,simulate

def market(n=390):
    dates=pd.bdate_range('2024-01-02',periods=3)
    a={k:np.empty((3,390)) for k in ('open','high','low','close','volume')}
    for i in range(3):
        for j in range(390):
            base=100+(i*78+j//5)*.05
            for k,v in dict(open=base,high=base+.04,low=base-.01,close=base+.02,volume=1000).items():a[k][i,j]=v
    return SimpleNamespace(arrays=a,dates=dates,lengths=np.full(3,n),valid=np.ones(3,bool),symbol='QQQ',quality=pd.DataFrame({'session_open':[str(d.date())+' 09:30:00-05:00' for d in dates]}))

def fixture(n=390):
    m=market(n);f=prepare(m,{})[-1];b=f['bars'][2];fast=b['ema_fast'];slow=b['ema_slow']
    for k,v in dict(open=fast+.01,high=fast+.06,low=(fast+slow)/2,close=fast+.05).items():m.arrays[k][-1,10:15]=v
    return m

def feature(m,cash=None):return prepare(m,cash or {})[-1]
def run(m,cfg=Config()):
    f=feature(m);return simulate(m,[f],cfg,f['date'],f['date'])

def test_ema_recursion_matches_pandas_previous_completed_bar():
    m=market();f=prepare(m,{})
    closes=np.concatenate([m.arrays['close'][i,4:390:5] for i in range(3)])
    for span,key in [(9,'ema_fast'),(20,'ema_slow')]:
        expected=pd.Series(closes).ewm(span=span,adjust=False).mean()
        assert f[2]['bars'][2][key]==pytest.approx(expected.iloc[157])
    assert f[0]['bars'][0]['state_reason']=='warmup_initial'
    assert f[0]['bars'][59]['state_reason']=='warmup_initial'
    assert f[0]['bars'][60]['state_reason']=='ready'

def test_signal_uses_prebar_ema_then_next_minute_open():
    m=fixture();s=signal(m,feature(m),Config())
    assert s['reason']=='eligible' and s['sign']==1 and s['signal_slot']==14 and s['entry_slot']==15
    assert s['ema_fast']>s['ema_slow'] and s['signal_low']>=s['ema_slow']

def test_no_future_price_or_volume_changes_signal():
    m=fixture();s=signal(m,feature(m),Config())
    m.arrays['high'][-1,15:]=999;m.arrays['close'][-1,300]=np.nan;m.arrays['volume'][:]=np.nan
    assert signal(m,feature(m),Config())==s

def test_cash_shift_all_prior_states_and_previous_close_not_slope():
    m=market();base=feature(m)['bars'][0];cash=feature(m,{str(m.dates[-1].date()):.5})['bars'][0]
    for key in ['ema_fast','ema_slow','previous_close']:assert cash[key]==pytest.approx(base[key]-.5)
    for key in ['slope_fast','slope_slow']:assert cash[key]==pytest.approx(base[key])

def test_extreme_cash_resets_even_an_older_nonpositive_slope_state():
    m=market();before=feature(m);div=before['opening_slow']-.025
    b=feature(m,{str(m.dates[-1].date()):div})['bars'][0]
    assert b['state_reason']=='unknown_indicator_history' and np.isnan(b['ema_fast'])

def test_indicator_reset_requires_sixty_whole_bars():
    m=market();m.arrays['close'][1,0]=np.nan;fs=prepare(m,{})
    assert fs[1]['bars'][1]['state_reason']=='unknown_indicator_history'
    assert fs[1]['bars'][60]['state_reason']=='unknown_indicator_history'
    assert fs[1]['bars'][61]['state_reason']=='ready'

def test_hole_before_first_signal_cannot_skip_to_later_setup():
    m=fixture();m.arrays['close'][-1,11]=np.nan
    assert signal(m,feature(m),Config())['reason']=='unknown_signal'
    m=fixture();m.arrays['close'][-1,1]=np.nan
    assert signal(m,feature(m),Config())['reason']=='unknown_indicator_history'

def test_initial_warmup_is_known_no_trade():
    m=market();f=prepare(m,{})[0];r=simulate(m,[f],Config(),f['date'],f['date'])
    assert r.trades.empty and r.daily.iloc[0].eligibility=='warmup_initial' and not r.daily.iloc[0].conditionally_excluded

def test_slope_and_momentum_ablations():
    m=fixture();f=feature(m);f['bars'][2]['slope_fast']=0
    assert signal(m,f,Config())['reason']=='no_pullback'
    assert signal(m,f,Config(require_slope=False))['reason']=='eligible'
    f=feature(m);f['bars'][2]['high']+=2
    assert signal(m,f,Config())['reason']=='no_pullback'
    assert signal(m,f,Config(momentum_fraction=0))['reason']=='eligible'

def test_controlled_zone_and_deep_pullback_ablation():
    m=fixture();f=feature(m);f['bars'][2]['low']=f['bars'][2]['ema_slow']-.1
    assert signal(m,f,Config())['reason']=='no_pullback'
    assert signal(m,f,Config(allow_deep=True))['reason']=='eligible'

def test_signal_must_return_above_fast_and_have_bullish_body():
    m=fixture();f=feature(m);b=f['bars'][2];b['close']=b['ema_fast']
    assert signal(m,f,Config())['reason']=='no_pullback'
    f=feature(m);f['bars'][2]['open']=f['bars'][2]['close']
    assert signal(m,f,Config())['reason']=='no_pullback'

def test_direction_filter_does_not_seek_later():
    m=fixture();assert signal(m,feature(m),Config(mode='short_only'))['reason']=='direction_filtered'

def test_cutoff_entry_not_allowed_at_1400():
    m=fixture();f=feature(m);setup=f['bars'][2].copy();f['bars'][2]['slope_fast']=0
    f['bars'][53].update({k:v for k,v in setup.items() if k not in ('left','entry_slot')})
    assert signal(m,f,Config())['reason']=='no_pullback'
    f['bars'][52].update({k:v for k,v in setup.items() if k not in ('left','entry_slot')})
    assert signal(m,f,Config())['entry_slot']==265

def test_float_noise_does_not_create_trend_or_slope():
    m=fixture();f=feature(m);b=f['bars'][2];b['slope_fast']=1e-12
    assert signal(m,f,Config())['reason']=='no_pullback'

def test_stop_rounded_outward_and_fixed_quantity_before_gap():
    m=fixture();f=feature(m);s=signal(m,f,Config());r=run(m);q=r.trades.iloc[0].quantity
    assert s['stop_price']<=s['signal_low']-.01+1e-12
    m.arrays['open'][-1,15]=s['stop_price']-.1
    t=run(m).trades.iloc[0];assert t.quantity==q and t.exit_reason=='entry_marketable_stop'
    small=run(m,Config(initial_capital=1000)).trades.iloc[0]
    assert small.quantity==9 and small.net_pnl==pytest.approx(-.88)

def test_stop_first_and_mae_excludes_exit_wick():
    m=fixture();m.arrays['low'][-1,16]=1;m.arrays['high'][-1,16]=999
    t=run(m).trades.iloc[0]
    assert t.ambiguous_bar and t.exit_reason=='stop_intrabar'
    assert t.mae_observed_usd==pytest.approx(t.quantity*(t.stop_price-t.entry_price))

def test_gap_target_no_improvement_and_gap_stop_adverse():
    m=fixture();m.arrays['open'][-1,16]=999;t=run(m).trades.iloc[0]
    assert t.exit_reason=='target_gap' and t.exit_reference==t.target_price
    m.arrays['open'][-1,16]=1;t=run(m).trades.iloc[0]
    assert t.exit_reason=='stop_gap' and t.exit_reference==1

def test_short_signal_and_borrow_minimum_one_day():
    m=fixture();f=feature(m);b=f['bars'][2]
    b.update(ema_fast=100,ema_slow=100.2,slope_fast=-.2,slope_slow=-.1,previous_close=99.8,open=99.9,high=100.1,low=99.7,close=99.75)
    for k,v in dict(open=99.75,high=99.8,low=99.7,close=99.75).items():m.arrays[k][-1,15:]=v
    s=signal(m,f,Config());assert s['sign']==-1 and s['stop_price']==100.11
    r=simulate(m,[f],Config(),f['date'],f['date']);t=r.trades.iloc[0]
    assert t.borrow_fee==pytest.approx(t.quantity*99.74*.01/360)

@pytest.mark.parametrize('n',[210,390])
def test_eod_open_before_final_wick(n):
    m=fixture(n);f=feature(m);s=signal(m,f,Config());entry=m.arrays['open'][-1,15]
    for k,v in dict(open=entry,high=entry+.01,low=entry-.01,close=entry).items():m.arrays[k][-1,15:]=v
    m.arrays['high'][-1,n-1]=999
    p=trace(m,f,s,Config());assert p['exit_slot']==n-1 and p['exit_reason']=='eod_open' and max(p['favorable'])<999

def test_missing_entry_and_active_hole_export_known_costs():
    m=fixture();m.arrays['open'][-1,15]=np.nan;r=run(m,Config(quality='resolved_prefix'))
    assert len(r.unresolved)==1 and r.unresolved.iloc[0].known_entry_commission==0
    m=fixture();m.arrays['close'][-1,16]=np.nan;r=run(m,Config(quality='resolved_prefix'))
    assert r.trades.empty and r.unresolved.iloc[0].known_entry_commission>0 and np.isnan(r.daily.iloc[0].observed_return)

def test_complete_day_filter_versus_resolved_prefix():
    m=fixture();m.valid[-1]=False;m.arrays['close'][-1,300]=np.nan
    assert run(m).trades.empty
    m.arrays['low'][-1,16]=1
    assert len(run(m,Config(quality='resolved_prefix')).trades)==1

def test_real_two_day_compounding_and_fill_cost_identity():
    m=fixture();f=prepare(m,{})[1:];r=simulate(m,f,Config(),f[0]['date'],f[-1]['date'])
    assert len(r.trades)>=1 and r.daily.equity.iloc[-1]==pytest.approx(100000+r.trades.net_pnl.sum())
    t=r.trades.iloc[0]
    assert t.net_pnl==pytest.approx(t.price_move_pnl-t.friction_cost-t.commission-t.borrow_fee)
    assert r.observed_close_drawdown_usd>0

@pytest.mark.parametrize('gap',[False,True])
def test_independent_ewm_segment_reconstruction(gap):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))
    from indicators import reconstruct
    m=market();cash={str(m.dates[-1].date()):.5}
    if gap:m.arrays['close'][1,1]=np.nan
    fs=prepare(m,cash);audit,_=reconstruct(m,cash)
    for f in fs:
        for b,x in zip(f['bars'],audit[f['index']]):
            assert b['valid']==x['valid']
            if b['valid']:
                assert b['state_reason']==x['state_reason']
                for field in ['ema_fast','ema_slow','slope_fast','slope_slow','previous_close']:
                    assert b[field]==pytest.approx(x[field],nan_ok=True)

@pytest.mark.parametrize('kw',[dict(bar_minutes=15),dict(slippage=-1),dict(mode='bad'),dict(momentum_fraction=1.1),dict(target_r=0),dict(quality='bad')])
def test_config_rejects_invalid(kw):
    with pytest.raises(ValueError):Config(**kw)
