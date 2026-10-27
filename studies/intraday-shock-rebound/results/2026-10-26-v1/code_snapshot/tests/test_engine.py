import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from shock.engine import Config,prepare,signal,trace,simulate

def market(days=24,n=390):
    dates=pd.bdate_range('2024-01-02',periods=days)
    a={k:np.full((days,390),v,dtype=float) for k,v in dict(open=100,high=100.2,low=99.8,close=100,volume=1000).items()}
    for i in range(days-1):
        c=100*np.exp((i%5-2)*.0005);a['close'][i,:]=c
    a['open'][-1,:30]=100;a['close'][-1,:30]=99;a['low'][-1,:30]=98.9;a['high'][-1,:30]=100.1
    for k,v in dict(open=99,close=99.2,high=99.3,low=98.95).items():a[k][-1,30:35]=v
    for k,v in dict(open=99.2,close=99.2,high=99.3,low=99.1).items():a[k][-1,35:]=v
    for k,v in dict(open=99.4,close=99.4,high=99.5,low=99.3).items():a[k][-1,n-1]=v
    return SimpleNamespace(arrays=a,dates=dates,lengths=np.full(days,n),valid=np.ones(days,bool),symbol='SPY',quality=pd.DataFrame({'session_open':[str(d.date())+' 09:30:00-05:00' for d in dates]}))

def feature(m):
    return dict(index=len(m.dates)-1,date=str(m.dates[-1].date()),session_minutes=int(m.lengths[-1]),bars=[dict(shock_end=29,valid=True,state_reason='ready',prior_count=20,
        shock_return=-.01,history_mean=0.,history_std=.003,shock_z=-3.,shock_close=99.,shock_low=98.9,shock_high=100.1,
        confirmation_valid=True,confirmation_open=99.,confirmation_close=99.2,confirmation_low=98.95,confirmation_high=99.3)])

def run(m,cfg=Config(),f=None):
    f=feature(m) if f is None else f
    return simulate(m,[f],cfg,f['date'],f['date'])

def test_matched_clock_statistics_exact_past20_ddof1():
    m=market();b=prepare(m,{})[-1]['bars'][0]
    r=np.log(m.arrays['close'][3:23,29]/m.arrays['open'][3:23,0])
    assert b['history_mean']==pytest.approx(r.mean()) and b['history_std']==pytest.approx(r.std(ddof=1))
    assert b['shock_z']==pytest.approx((np.log(.99)-r.mean())/r.std(ddof=1))

def test_current_day_and_future_prices_not_in_history_statistics():
    m=market();before=prepare(m,{})[-1]['bars'][0]
    m.arrays['close'][-1,29]=98;m.arrays['low'][-1,29]=97;m.arrays['high'][-1,300]=999
    after=prepare(m,{})[-1]['bars'][0]
    assert (after['history_mean'],after['history_std'])==(before['history_mean'],before['history_std'])
    assert after['shock_return']!=before['shock_return']

def test_same_day_price_scaling_and_cash_do_not_change_return_features():
    m=market();x=prepare(m,{})[-1]['bars'][0]
    for k in ['open','high','low','close']:m.arrays[k][3,:]*=2
    y=prepare(m,{'2024-01-05':7})[-1]['bars'][0]
    assert y['shock_z']==pytest.approx(x['shock_z'])

def test_past_half_session_skipped_only_at_structurally_closed_clock():
    m=market(45);m.lengths[30]=210
    f=prepare(m,{})[-1];b=next(b for b in f['bars'] if b['shock_end']==224)
    idx=[i for i in range(44) if m.lengths[i]>224][-20:]
    expected=np.log(m.arrays['close'][idx,224]/m.arrays['open'][idx,195])
    assert b['prior_count']==20 and b['history_mean']==pytest.approx(expected.mean())

def test_missing_historical_bar_not_silently_skipped():
    m=market();m.arrays['close'][10,12]=np.nan
    f=prepare(m,{})[-1]
    assert f['bars'][0]['state_reason']=='unknown_history'
    assert signal(m,f,Config())['reason']=='unknown_history'

def test_warmup_is_known_no_order_and_zero_variance_is_known():
    m=market();f=prepare(m,{})[5]
    assert signal(m,f,Config())['reason']=='warmup_initial'
    m.arrays['close'][:-1,:]=100
    assert prepare(m,{})[-1]['bars'][0]['state_reason']=='zero_variance'

def test_signal_confirmed_close_then_next_open_and_outward_stop():
    m=market();s=signal(m,feature(m),Config())
    assert (s['signal_slot'],s['entry_slot'],s['sizing_price'],s['stop_price'])==(34,35,99.2,98.89)
    assert s['sign']==1 and s['confirmation']

@pytest.mark.parametrize('field,value',[('shock_return',.01),('shock_z',-1.99),('confirmation_close',98.9),('confirmation_open',99.3)])
def test_nonqualifying_conditions_are_filtered(field,value):
    m=market();f=feature(m);f['bars'][0][field]=value
    assert signal(m,f,Config())['reason']=='no_rebound'

def test_confirmation_close_must_exceed_shock_close():
    m=market();f=feature(m);f['bars'][0].update(confirmation_open=98.7,confirmation_close=98.8)
    assert signal(m,f,Config())['reason']=='no_rebound'

def test_invalid_confirmation_only_matters_after_eligible_shock():
    m=market();f=feature(m);f['bars'][0]['confirmation_valid']=False
    assert signal(m,f,Config())['reason']=='unknown_confirmation'
    f['bars'][0]['shock_z']=0
    assert signal(m,f,Config())['reason']=='no_rebound'

def test_no_confirmation_does_not_read_future_confirmation():
    m=market();f=feature(m);f['bars'][0]['confirmation_valid']=False
    s=signal(m,f,Config(confirmation=False))
    assert s['entry_slot']==30 and s['sizing_price']==99 and not s['confirmation']

def test_threshold_sensitivity_and_no_z_control_preserve_negative_return():
    m=market();f=feature(m);f['bars'][0]['shock_z']=-1.7
    assert signal(m,f,Config(z_threshold=1.5))['reason']=='eligible'
    assert signal(m,f,Config())['reason']=='no_rebound'
    assert signal(m,f,Config(z_filter=False))['reason']=='eligible'
    f['bars'][0]['shock_return']=.01
    assert signal(m,f,Config(z_filter=False))['reason']=='no_rebound'

def test_short_mirror_direction_and_stop():
    m=market();f=feature(m);f['bars'][0].update(shock_return=.01,shock_z=3,shock_close=101,shock_high=101.1,confirmation_open=101,confirmation_close=100.8,confirmation_high=101.05)
    s=signal(m,f,Config(mode='short'))
    assert s['sign']==-1 and s['stop_price']==101.11 and s['sizing_price']==100.8

def test_unknown_earlier_window_cannot_be_treated_as_no_signal():
    m=market();f=feature(m);b=f['bars'][0].copy();b['shock_end']=34;f['bars'].append(b);f['bars'][0]['valid']=False
    assert signal(m,f,Config())['reason']=='unknown_signal'

def test_first_resolved_signal_ignores_unknown_later_window():
    m=market();f=feature(m);b=f['bars'][0].copy();b.update(shock_end=34,valid=False);f['bars'].append(b)
    assert signal(m,f,Config())['entry_slot']==35

@pytest.mark.parametrize('n,last',[(390,330),(210,150)])
def test_last_entry_one_hour_before_close_inclusive(n,last):
    m=market(n=n);f=feature(m);f['bars'][0]['shock_end']=last-6
    assert signal(m,f,Config())['entry_slot']==last
    f['bars'][0]['shock_end']+=5
    assert signal(m,f,Config())['reason']=='no_rebound'

def test_quantity_uses_signal_close_not_future_open():
    m=market();q=run(m).trades.iloc[0].quantity
    m.arrays['open'][-1,35]=98
    assert run(m).trades.iloc[0].quantity==q

def test_gap_below_stop_is_immediate_loss_of_costs_and_no_retro_cancel():
    m=market();m.arrays['open'][-1,35]=98;t=run(m).trades.iloc[0]
    assert t.exit_reason=='entry_marketable_stop' and t.net_pnl<0 and t.entry_slot==t.exit_slot

def test_stop_intrabar_and_target_stop_same_bar_prioritizes_stop():
    m=market();m.arrays['low'][-1,36]=98;m.arrays['high'][-1,36]=105;t=run(m).trades.iloc[0]
    assert t.exit_reason=='stop_intrabar' and t.ambiguous_bar and t.exit_reference==98.89

def test_stop_gap_at_bad_open_and_target_gap_no_price_improvement():
    m=market();m.arrays['open'][-1,36]=98;t=run(m).trades.iloc[0]
    assert t.exit_reason=='stop_gap' and t.exit_reference==98
    m=market();m.arrays['open'][-1,36]=101;t=run(m).trades.iloc[0]
    assert t.exit_reason=='target_gap' and t.exit_reference==pytest.approx(99.82)

@pytest.mark.parametrize('n',[210,390])
def test_exit_at_last_open_before_last_wick(n):
    m=market(n=n);m.arrays['low'][-1,n-1]=1;m.arrays['high'][-1,n-1]=999;t=run(m).trades.iloc[0]
    assert t.exit_reason=='eod_open' and t.exit_slot==n-1 and t.mae_observed_usd>-1000

def test_missing_entry_and_active_minute_are_unresolved():
    m=market();m.arrays['open'][-1,35]=np.nan;r=run(m,Config(quality='resolved_prefix'))
    assert r.trades.empty and r.unresolved.iloc[0].known_entry_commission==0
    m=market();m.arrays['close'][-1,36]=np.nan;r=run(m,Config(quality='resolved_prefix'))
    assert r.trades.empty and r.unresolved.iloc[0].known_entry_commission>0 and pd.isna(r.daily.iloc[0].observed_return)

def test_future_quality_filter_removed_in_prefix_when_exit_already_resolved():
    m=market();m.valid[-1]=False;m.arrays['close'][-1,300]=np.nan;m.arrays['low'][-1,36]=98
    assert run(m).trades.empty and len(run(m,Config(quality='resolved_prefix')).trades)==1

def test_cost_identity_and_minimum_commission():
    t=run(market(),Config(initial_capital=1000)).trades.iloc[0]
    assert t.quantity==10 and t.commission==.7 and t.friction_cost==.2 and t.borrow_fee==0
    assert t.net_pnl==pytest.approx(t.price_move_pnl-t.friction_cost-t.commission)

def test_short_costs_include_borrow():
    m=market();f=feature(m);f['bars'][0].update(shock_return=.01,shock_z=3,shock_close=101,shock_high=101.1,confirmation_open=101,confirmation_close=100.8,confirmation_high=101.05)
    t=run(m,Config(mode='short'),f).trades.iloc[0]
    assert t.borrow_fee==pytest.approx(t.quantity*t.entry_price*.01/360)

def test_zero_quantity_and_account_compounding():
    m=market();assert run(m,Config(initial_capital=1)).trades.empty
    f=feature(m);f2={**f,'date':'2024-02-05'};r=simulate(m,[f,f2],Config(),f['date'],f2['date'])
    assert r.trades.iloc[1].equity_before==pytest.approx(r.trades.iloc[0].equity_after)
    assert r.daily.equity.iloc[-1]==pytest.approx(100000+r.trades.net_pnl.sum())

def test_invalid_config_rejected():
    with pytest.raises(ValueError):Config(z_threshold=0)
    with pytest.raises(ValueError):Config(mode='both')

def test_zero_variance_needs_no_current_price_to_rule_out_order():
    m=market();f=feature(m);f['bars'][0].update(state_reason='zero_variance',valid=False)
    assert signal(m,f,Config())['reason']=='no_rebound'

def test_future_sessions_do_not_change_past_features():
    m=market();before=prepare(m,{})[21]['bars'][0]
    for k in ['open','high','low','close']:m.arrays[k][22:,:]*=3
    after=prepare(m,{})[21]['bars'][0]
    assert after['shock_z']==before['shock_z'] and after['history_std']==before['history_std']

def test_independent_feature_reconstruction_matches_known_history():
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))
    from features import reconstruct
    m=market();m.lengths[3]=210;m.arrays['close'][10,220]=np.nan
    expected=prepare(m,{});actual,_=reconstruct(m)
    for i in [5,21,23]:
        for x,y in zip(expected[i]['bars'],actual[i]):
            assert x['state_reason']==y['state_reason'] and x['valid']==y['valid']
            for k in ['shock_return','history_mean','history_std','shock_z']:
                assert x[k]==pytest.approx(y[k],nan_ok=True,abs=1e-9)

def test_full_scalar_audit_runs_with_actual_config_schema(tmp_path,monkeypatch):
    import importlib.util,json,copy
    from dataclasses import asdict
    from orb.analysis import summarize
    root=Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root/'audit'))
    def module(name,path):
        spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
    runner=module('synthetic_shock_runner',root/'scripts/run_study.py')
    auditor=module('synthetic_shock_audit',root/'audit/independent.py')
    m=market();q=copy.deepcopy(m);q.symbol='QQQ';markets={'SPY':m,'QQQ':q}
    out=tmp_path/'run';out.mkdir();(tmp_path/'audit').mkdir();rows=[]
    (out/'PRE_EXECUTION_PROTOCOL.json').write_text('{}',encoding='utf-8')
    date=str(m.dates[-1].date())
    for symbol,data in markets.items():
        fs=prepare(data,{})
        for name,cfg in runner.specifications():
            label=symbol+'_SYNTHETIC_'+name;folder=out/label;folder.mkdir()
            r=simulate(data,fs,cfg,date,date)
            stats=dict(label=label,symbol=symbol,period='SYNTHETIC',variant=name,start=date,end=date,**asdict(cfg),**summarize(r))
            rows.append(stats)
            for filename,value in [('trades.csv',r.trades),('daily.csv',r.daily),('unresolved.csv',r.unresolved)]:value.to_csv(folder/filename,index=False)
            (folder/'summary.json').write_text(json.dumps(stats),encoding='utf-8')
    pd.DataFrame(rows).to_csv(out/'comparison_all.csv',index=False)
    monkeypatch.setattr(auditor,'ROOT',tmp_path)
    monkeypatch.setattr(auditor,'load_sources',lambda:(markets,{'SPY':{},'QQQ':{}},{}))
    monkeypatch.setattr(sys,'argv',['audit','--out',str(out)])
    auditor.main()
    receipt=json.loads((tmp_path/'audit/AUDIT_RESULTS.json').read_text(encoding='utf-8'))
    assert receipt['status']=='passed' and receipt['scenario_count']==24 and not receipt['failures']

@pytest.mark.parametrize('mode,raw',[('long',.01),('short',-.01)])
def test_known_wrong_sign_does_not_need_unknown_baseline(mode,raw):
    m=market();f=feature(m);f['bars'][0].update(state_reason='unknown_history',shock_return=raw)
    assert signal(m,f,Config(mode=mode))['reason']=='no_rebound'
