import sys,copy,json,importlib.util
from pathlib import Path
from types import SimpleNamespace
from dataclasses import asdict
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from retest.engine import Config,prepare,signal,simulate

def bar(m,left,op,hi,lo,cl,i=0):
    for k,v in dict(open=op,high=hi,low=lo,close=cl).items():m.arrays[k][i,left:left+5]=v

def market(n=390):
    dates=pd.DatetimeIndex(['2024-01-02','2024-01-03','2024-01-04'])
    a={k:np.full((3,390),v,dtype=float) for k,v in dict(open=100.15,high=100.25,low=100.05,close=100.15,volume=1000).items()}
    m=SimpleNamespace(arrays=a,dates=dates,lengths=np.full(3,n),valid=np.ones(3,bool),symbol='SPY',quality=pd.DataFrame({'session_open':[str(d.date())+' 09:30:00-05:00' for d in dates]}))
    for i in range(3):
        for left in [0,5,10]:bar(m,left,99.6,100,99,99.8,i)
        bar(m,15,99.9,100.3,99.85,100.2,i)
        bar(m,20,100.05,100.25,99.95,100.15,i)
        for k,v in dict(open=100.35,high=100.4,low=100.3,close=100.35).items():a[k][i,n-1]=v
    return m

def fs(m):return prepare(m,{})
def sig(m,cfg=Config()):return signal(m,fs(m)[0],cfg)
def run(m,cfg=Config()):
    f=fs(m)[0];return simulate(m,[f],cfg,f['date'],f['date'])

def mirror(m):
    a=m.arrays;old={k:a[k].copy() for k in ['open','high','low','close']}
    for k in ['open','close']:a[k][:]=200-old[k]
    a['high'][:]=200-old['low'];a['low'][:]=200-old['high'];return m

def test_fixed_range_and_distinct_retest_next_open():
    s=sig(market())
    assert (s['range_high'],s['range_low'],s['breakout_level'])==(100,99,100)
    assert (s['breakout_slot'],s['signal_slot'],s['entry_slot'],s['wait_bars'])==(19,24,25,1)
    assert s['stop_price']==99.94 and s['sizing_price']==100.15 and s['sign']==1

def test_wick_alone_is_not_a_breakout():
    m=market()
    for left in range(15,125,5):bar(m,left,99.6,101,98,99.8)
    assert sig(m)['reason']=='no_breakout'

def test_breakout_bar_cannot_be_its_own_retest():
    m=market();s=sig(m,Config(entry_mode='breakout'))
    assert s['entry_slot']==20 and s['wait_bars']==0 and s['stop_price']==99.84
    assert sig(m)['entry_slot']==25

def test_first_touch_failing_close_cancels_later_good_retest():
    m=market();bar(m,20,100.05,100.2,99.9,99.95);bar(m,25,100.05,100.3,99.95,100.15)
    assert sig(m)['reason']=='retest_failed'

def test_first_touch_failing_body_cancels_day():
    m=market();bar(m,20,100.2,100.3,99.95,100.15)
    assert sig(m)['reason']=='retest_failed'

def test_equal_level_close_is_not_confirmation():
    m=market();bar(m,20,99.95,100.2,99.9,100)
    assert sig(m)['reason']=='retest_failed'

def test_retest_can_start_inside_range_but_must_reclaim_before_entry():
    m=market();bar(m,20,99.9,100.3,99.8,100.15)
    assert sig(m)['entry_slot']==25 and sig(m)['stop_price']==99.79

def test_last_wait_bar_included_and_next_bar_ignored():
    m=market()
    for left in range(20,55,5):bar(m,left,100.2,100.4,100.1,100.25)
    bar(m,45,100.05,100.3,99.95,100.15)
    assert sig(m)['wait_bars']==6 and sig(m)['entry_slot']==50
    bar(m,45,100.2,100.4,100.1,100.25);bar(m,50,100.05,100.3,99.95,100.15)
    assert sig(m)['reason']=='retest_expired'

def test_wait_sensitivity_is_not_a_restart():
    m=market()
    for left in range(20,40,5):bar(m,left,100.2,100.4,100.1,100.25)
    bar(m,40,100.05,100.3,99.95,100.15)
    assert sig(m,Config(max_wait_bars=3))['reason']=='retest_expired'
    assert sig(m,Config(max_wait_bars=12))['entry_slot']==45

def test_unknown_waiting_bar_does_not_become_absent_touch():
    m=market();m.arrays['close'][0,22]=np.nan
    assert sig(m)['reason']=='unknown_signal'

def test_unknown_after_expiry_or_failure_is_not_needed():
    m=market();bar(m,20,100.2,100.3,99.95,100.15);m.arrays['close'][0,30]=np.nan
    assert sig(m)['reason']=='retest_failed'
    m=market()
    for left in range(20,55,5):bar(m,left,100.2,100.4,100.1,100.25)
    m.arrays['close'][0,55]=np.nan
    assert sig(m)['reason']=='retest_expired'

def test_unknown_opening_range_is_not_skipped():
    m=market();m.arrays['close'][0,2]=np.nan
    assert sig(m)['reason']=='unknown_range'

def test_zero_range_is_known_no_order():
    m=market()
    for k in ['open','high','low','close']:m.arrays[k][0,:15]=100
    assert sig(m)['reason']=='zero_range'

def test_unknown_bar_before_first_breakout_is_not_skipped():
    m=market();m.arrays['close'][0,17]=np.nan
    assert sig(m)['reason']=='unknown_signal'

def test_direction_filter_uses_first_breakout_only():
    m=market();assert sig(m,Config(mode='short_only'))['reason']=='direction_filtered'
    assert sig(m,Config(mode='long_only'))['entry_slot']==25
    s=sig(mirror(market()))
    assert s['sign']==-1 and s['breakout_level']==100 and s['stop_price']==100.06

@pytest.mark.parametrize('n',[210,390])
def test_cutoff_entry_included_for_normal_and_half_days(n):
    m=market(n)
    for left in range(15,110,5):bar(m,left,99.6,100,99,99.8)
    bar(m,110,99.9,100.3,99.85,100.2);bar(m,115,100.05,100.3,99.95,100.15)
    assert sig(m)['entry_slot']==120
    bar(m,115,100.2,100.4,100.1,100.25)
    assert sig(m)['reason']=='entry_cutoff'

def test_prices_after_signal_do_not_change_signal_or_sizing():
    m=market();s=sig(m);q=run(m).trades.iloc[0].quantity
    m.arrays['open'][0,25]=98;m.arrays['high'][0,200]=999
    assert sig(m)==s and run(m).trades.iloc[0].quantity==q

def test_future_day_volume_and_cash_not_in_range_signal():
    m=market();before=sig(m)
    m.arrays['volume'][:]=np.nan
    for k in ['open','high','low','close']:m.arrays[k][1:,:]*=5
    f=prepare(m,{'2024-01-02':7})[0]
    assert signal(m,f,Config())==before

def test_gap_through_stop_is_immediate_and_costly():
    m=market();m.arrays['open'][0,25]=98;t=run(m).trades.iloc[0]
    assert t.exit_reason=='entry_marketable_stop' and t.exit_slot==25 and t.net_pnl<0

def test_stop_gap_and_target_gap_no_price_improvement():
    m=market();m.arrays['open'][0,26]=99;t=run(m).trades.iloc[0]
    assert t.exit_reason=='stop_gap' and t.exit_reference==99
    m=market();m.arrays['open'][0,26]=102;t=run(m).trades.iloc[0]
    assert t.exit_reason=='target_gap' and t.exit_reference==pytest.approx(100.57)

def test_simultaneous_stop_target_prioritizes_stop():
    m=market();m.arrays['low'][0,26]=99;m.arrays['high'][0,26]=102;t=run(m).trades.iloc[0]
    assert t.ambiguous_bar and t.exit_reason=='stop_intrabar' and t.exit_reference==99.94

@pytest.mark.parametrize('n',[210,390])
def test_last_open_exit_before_its_wick(n):
    m=market(n);m.arrays['low'][0,n-1]=1;m.arrays['high'][0,n-1]=999;t=run(m).trades.iloc[0]
    assert t.exit_reason=='eod_open' and t.exit_slot==n-1 and t.mae_observed_usd>-1000

def test_missing_entry_and_active_data_are_unresolved():
    m=market();m.arrays['open'][0,25]=np.nan;r=run(m,Config(quality='resolved_prefix'))
    assert r.trades.empty and r.unresolved.iloc[0].known_entry_commission==0
    m=market();m.arrays['close'][0,26]=np.nan;r=run(m,Config(quality='resolved_prefix'))
    assert r.trades.empty and r.unresolved.iloc[0].known_entry_commission>0 and pd.isna(r.daily.iloc[0].observed_return)

def test_future_quality_filter_and_resolved_prefix():
    m=market();m.valid[0]=False;m.arrays['close'][0,300]=np.nan;m.arrays['low'][0,26]=99
    assert run(m).trades.empty and len(run(m,Config(quality='resolved_prefix')).trades)==1

def test_minimum_fees_borrow_and_cost_identity():
    t=run(market(),Config(initial_capital=1000)).trades.iloc[0]
    assert t.quantity==9 and t.commission==.7 and t.friction_cost==.18 and t.borrow_fee==0
    assert t.net_pnl==pytest.approx(t.price_move_pnl-t.friction_cost-t.commission)
    t=run(mirror(market())).trades.iloc[0]
    assert t.borrow_fee==pytest.approx(t.quantity*t.entry_price*.01/360)

def test_zero_quantity_and_compounding():
    m=market();assert run(m,Config(initial_capital=1)).trades.empty
    f=fs(m);r=simulate(m,f,Config(),f[0]['date'],f[-1]['date'])
    assert len(r.trades)==3 and r.trades.iloc[1].equity_before==pytest.approx(r.trades.iloc[0].equity_after)
    assert r.daily.equity.iloc[-1]==pytest.approx(100000+r.trades.net_pnl.sum())

def test_invalid_config_rejected():
    with pytest.raises(ValueError):Config(max_wait_bars=0)
    with pytest.raises(ValueError):Config(mode='wrong')

def test_separate_bar_aggregation_handles_missing_minutes():
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'audit'))
    from bars import reconstruct
    m=market();m.arrays['low'][0,71]=np.nan
    a=fs(m);b,_=reconstruct(m)
    for x,y in zip(a[0]['bars'],b[0]):
        assert x['valid']==y['valid'] and x['entry_slot']==y['entry_slot']
        if x['valid']:
            for k in ['open','high','low','close']:assert x[k]==pytest.approx(y[k])

@pytest.mark.parametrize('case',['ordinary','missing_entry','missing_active','failed_touch','expired','half_day','cutoff'])
def test_full_scalar_audit_matches_config_and_exports(tmp_path,monkeypatch,case):
    from orb.analysis import summarize
    root=Path(__file__).resolve().parents[1];monkeypatch.syspath_prepend(str(root/'audit'))
    def module(name,path):
        spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
    runner=module('test_retest_runner',root/'scripts/run_study.py');audit=module('test_retest_audit',root/'audit/independent.py')
    m=market(210 if case=='half_day' else 390)
    if case=='missing_entry':m.arrays['open'][0,25]=np.nan
    if case=='missing_active':m.arrays['close'][0,26]=np.nan
    if case=='failed_touch':bar(m,20,100.2,100.3,99.95,100.15)
    if case=='expired':
        for left in range(20,125,5):bar(m,left,100.2,100.4,100.1,100.25)
    if case=='cutoff':
        for left in range(15,110,5):bar(m,left,99.6,100,99,99.8)
        bar(m,110,99.9,100.3,99.85,100.2);bar(m,115,100.05,100.3,99.95,100.15)
    if case.startswith('missing_'):m.valid[0]=False
    q=mirror(copy.deepcopy(m));q.symbol='QQQ';markets={'SPY':m,'QQQ':q}
    out=tmp_path/'run';out.mkdir();(tmp_path/'audit').mkdir();rows=[]
    date=fs(m)[0]['date']
    frozen=dict(symbols=['SPY','QQQ'],periods={'SYNTHETIC':[date,date]},specifications={name:asdict(cfg) for name,cfg in runner.specifications()},executions=24)
    (out/'PRE_EXECUTION_PROTOCOL.json').write_text(json.dumps(frozen),encoding='utf-8')
    for symbol,data in markets.items():
        f=fs(data);date=f[0]['date']
        for name,cfg in runner.specifications():
            label=symbol+'_SYNTHETIC_'+name;folder=out/label;folder.mkdir();r=simulate(data,f,cfg,date,date)
            stats=dict(label=label,symbol=symbol,period='SYNTHETIC',variant=name,start=date,end=date,**asdict(cfg),**summarize(r));rows.append(stats)
            for filename,value in [('trades.csv',r.trades),('daily.csv',r.daily),('unresolved.csv',r.unresolved)]:value.to_csv(folder/filename,index=False)
            runner.write_json(folder/'summary.json',stats)
    pd.DataFrame(rows).to_csv(out/'comparison_all.csv',index=False)
    monkeypatch.setattr(audit,'ROOT',tmp_path);monkeypatch.setattr(audit,'load_sources',lambda:(markets,{'SPY':{},'QQQ':{}},{}));monkeypatch.setattr(sys,'argv',['audit','--out',str(out)])
    audit.main();x=json.loads((tmp_path/'audit/AUDIT_RESULTS.json').read_text(encoding='utf-8'))
    assert x['status']=='passed' and x['scenario_count']==24 and not x['failures']
