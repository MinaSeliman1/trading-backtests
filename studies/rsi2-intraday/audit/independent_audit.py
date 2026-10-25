"""Independent RSI study audit: no strategy/analysis arithmetic helpers imported.

The legacy loader is used only to retrieve and hash-validate the frozen local
sources. Indicators, decisions, executions, accounts and statistics below are
reimplemented from the protocol with Python math/Decimal.
"""
from pathlib import Path
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
from collections import Counter
import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT.parent / 'opening-range-5m'))
sys.path.insert(0, str(ROOT.parent / 'closing-momentum'))
sys.path.insert(0, str(ROOT.parent / 'intraday-momentum-noise-area'))
import pandas as pd

D = lambda value: Decimal(str(value))
checks = Counter()
failures = []
failure_counts = Counter()
max_errors = Counter()


def check(ok, kind, context):
    checks[kind] += 1
    if not ok:
        failure_counts[kind] += 1
        if len(failures) < 100:
            failures.append({'kind': kind, 'context': context})
        checks['FAILED'] += 1


def near(actual, expected, kind, context, tol=1e-6):
    try:
        a = math.nan if actual in ('',None) else float(actual)
        b = math.nan if expected in ('',None) else float(expected)
        equal = (math.isnan(a) and math.isnan(b)) or abs(a-b) <= tol
        if math.isfinite(a) and math.isfinite(b):
            max_errors[kind] = max(max_errors[kind], abs(a-b))
    except (TypeError, ValueError):
        equal = actual is None and expected is None
    check(equal, kind, f'{context}: actual={actual}, expected={expected}')


def rows(path):
    with path.open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def finite_positive(value):
    return math.isfinite(value) and value > 0


def minute_valid(values):
    o, h, l, c, v = values
    return (all(math.isfinite(x) for x in values) and min(o,h,l,c) > 0
            and v >= 0 and h >= max(o,h,l,c) and l <= min(o,h,l,c))


def smooth(values, length):
    result = [math.nan] * len(values)
    if len(values) < length or not all(math.isfinite(x) for x in values[:length]):
        return result
    current = math.fsum(values[:length]) / length
    result[length-1] = current
    for i in range(length, len(values)):
        if not math.isfinite(values[i]):
            break
        current = ((length-1)*current + values[i]) / length
        result[i] = current
    return result


def independent_features(market, cash):
    history, result, cumulative = [], [], 0.
    for index, stamp in enumerate(market.dates):
        date = str(stamp.date())
        n = int(market.lengths[index])
        raw = [[float(market.arrays[k][index,j]) for k in ('open','high','low','close','volume')] for j in range(n)]
        good = [minute_valid(values) for values in raw]
        blocks, usable = [], []
        for left in range(0,n,5):
            block = raw[left:left+5]
            ok = len(block)==5 and all(good[left:left+5])
            usable.append(ok)
            blocks.append((block[0][0], max(x[1] for x in block), min(x[2] for x in block), block[-1][3]) if ok else (math.nan,)*4)
        changes = [blocks[j][3]-blocks[j-1][3] for j in range(1,len(blocks))]
        gains = smooth([max(x,0.) for x in changes],2)
        losses = smooth([max(-x,0.) for x in changes],2)
        rsi = [math.nan] * len(blocks)
        for j,(g,l) in enumerate(zip(gains,losses),1):
            if math.isfinite(g+l):
                rsi[j] = 50. if g==l==0 else 100. if l==0 else 100.-100./(1.+g/l)
        tr = [h-l if j==0 else max(h-l,abs(h-blocks[j-1][3]),abs(l-blocks[j-1][3])) for j,(_,h,l,_) in enumerate(blocks)]
        atr = smooth(tr,14)
        previous = history[-1] if history else math.nan
        prior = history[-200:]
        reason = 'warmup200' if index<200 else 'invalid_prior_close' if not all(math.isfinite(x) for x in prior) else 'eligible'
        average = math.fsum(prior)/200 if len(prior)==200 else math.nan
        trend = (1 if previous>average else -1 if previous<average else 0) if reason=='eligible' else 0
        result.append(dict(date=date,index=index,n=n,raw=raw,good=good,blocks=blocks,usable=usable,rsi=rsi,atr=atr,prior_close=previous,prior_sma=average,trend=trend,regime_reason=reason))
        cumulative += float(cash.get(date,0.))
        close = raw[-1][3]
        history.append(close+cumulative if finite_positive(close) else math.nan)
    return result


def setup(f,cfg):
    if cfg['use_regime'] and f['regime_reason']!='eligible':
        return f['regime_reason'], None
    allowed = []
    if cfg['mode'] in ('long_only','both') and (not cfg['use_regime'] or f['trend']==1):
        allowed.append(1)
    if cfg['mode'] in ('short_only','both') and (not cfg['use_regime'] or f['trend']==-1):
        allowed.append(-1)
    if not allowed:
        return 'regime_filtered',None
    for b,bar in enumerate(f['blocks']):
        entry=(b+1)*5
        if entry>=min(330,f['n']-1):
            break
        if not f['usable'][b]:
            return 'unknown_signal',None
        if entry<30 or not finite_positive(f['atr'][b]):
            continue
        r=f['rsi'][b]
        side=1 if 1 in allowed and r<cfg['entry_threshold'] else -1 if -1 in allowed and r>100-cfg['entry_threshold'] else 0
        if side:
            close=bar[3]
            stop=(D(close)-side*D(cfg['stop_atr'])*D(f['atr'][b])).quantize(D('.01'),rounding=ROUND_FLOOR if side==1 else ROUND_CEILING)
            if stop<=0:
                return 'invalid_stop',None
            return 'eligible',dict(sign=side,signal_slot=entry-1,entry_slot=entry,sizing_price=close,stop_price=float(stop),signal_rsi=r,signal_atr=f['atr'][b])
    return 'no_signal',None


def execution(f,s,cfg):
    side,stop,left=s['sign'],s['stop_price'],s['entry_slot']
    entry=f['raw'][left][0]
    if not finite_positive(entry):
        return None,('missing_entry_open',left)
    closes,adverse,favorable=[],[entry],[entry]
    scheduled=signal=None
    resolution='bar_open'
    for j in range(left,f['n']):
        o,h,l,c,_=f['raw'][j]
        if not finite_positive(o):
            return None,('missing_active_open',j)
        if side*(o-stop)<=0:
            ref=o;reason='entry_marketable_stop' if j==left else 'stop_gap';break
        if scheduled==j:
            ref=o;reason='indicator_next_open';break
        if j==f['n']-1:
            ref=o;reason='eod_open';break
        if not f['good'][j]:
            return None,('invalid_active_bar',j)
        if (l<=stop if side==1 else h>=stop):
            ref=stop;reason='stop_intrabar';resolution='intrabar_minute_unknown';break
        closes.append(c);adverse.append(l if side==1 else h);favorable.append(h if side==1 else l)
        if (j+1)%5==0:
            r=f['rsi'][j//5]
            if not math.isfinite(r):
                return None,('unknown_exit_indicator',j)
            if (r>cfg['exit_threshold'] if side==1 else r<100-cfg['exit_threshold']):
                scheduled=j+1;signal=j
    adverse.append(ref);favorable.append(ref)
    return dict(entry_reference=entry,exit_reference=ref,exit_slot=j,exit_reason=reason,exit_signal_slot=signal,exit_resolution=resolution,holding_minutes_upper=j-left+int(resolution=='intrabar_minute_unknown'),closes=closes,adverse=adverse,favorable=favorable),None


def decimal_trade(t,cfg,label):
    q,side=D(t['quantity']),int(t['sign'])
    entry,exit=D(t['entry_reference']),D(t['exit_reference'])
    slip=D(cfg['slippage']);fee=2*max(D('.35'),q*D('.0035'))
    borrow=q*(entry+side*slip)*D('.01')/D(360) if side<0 else D(0)
    expected={'entry_price':entry+side*slip,'exit_price':exit-side*slip,'price_move_pnl':q*side*(exit-entry),'friction_cost':2*q*slip,'commission':fee,'borrow_fee':borrow}
    expected['gross_pnl']=expected['price_move_pnl']-expected['friction_cost']
    expected['net_pnl']=expected['gross_pnl']-fee-borrow
    for key,value in expected.items():
        near(t[key],value,'decimal_'+key,f'{label}/{t["date"]}')
    risk=side*(D(t['sizing_price'])-D(t['stop_price']))
    size=int(min(D(t['equity_before'])*D(cfg['leverage_cap'])/D(t['sizing_price']),D(t['equity_before'])*D(cfg['risk_budget'])/risk).to_integral_value(rounding=ROUND_FLOOR))
    near(t['quantity'],size,'decimal_quantity',f'{label}/{t["date"]}',0)
    near(t['equity_after'],D(t['equity_before'])+expected['net_pnl'],'decimal_account',f'{label}/{t["date"]}')
    return expected['net_pnl']


def scenario(folder,summary,cfg,features,market):
    label=summary['label'];trades=rows(folder/'trades.csv');daily=rows(folder/'daily.csv');unresolved=rows(folder/'unresolved.csv')
    trade_map={t['date']:t for t in trades};unresolved_map={t['date']:t for t in unresolved}
    check(len(trade_map)==len(trades),'one_trade',label)
    selected=[f for f in features if summary['start']<=f['date']<=summary['end']]
    check([f['date'] for f in selected]==[d['date'] for d in daily],'calendar',label)
    capital=cfg['initial_capital'];decimal_capital=D(capital);peak=capital;dd=dd_usd=0.;traded=0
    for f,d in zip(selected,daily):
        date=f['date'];context=f'{label}/{date}';before=capital;net=0.;qty=upper=0;marks=[capital]
        reason,s=setup(f,cfg);excluded=reason=='unknown_signal'
        if reason=='eligible' and cfg['quality']=='complete_days' and not market.valid[f['index']]:
            reason='excluded_incomplete_day';excluded=True
        if capital<=0:
            reason='insolvent'
        if reason=='eligible':
            side=s['sign'];risk=side*(D(s['sizing_price'])-D(s['stop_price']))
            qty=int(min(D(before)*D(cfg['leverage_cap'])/D(s['sizing_price']),D(before)*D(cfg['risk_budget'])/risk).to_integral_value(rounding=ROUND_FLOOR))
            if qty<=0:
                reason='zero_quantity'
            else:
                p,error=execution(f,s,cfg)
                if error:
                    reason='unresolved_execution';excluded=True;qty=0
                    u=unresolved_map.get(date)
                    check(u is not None,'unresolved_presence',context)
                    if u:
                        check((u['reason'],int(u['first_unknown_slot']))==error,'unresolved_reason',context)
                else:
                    traded+=1;t=trade_map.get(date)
                    check(t is not None,'trade_presence',context)
                    entry=p['entry_reference']+side*cfg['slippage'];exit=p['exit_reference']-side*cfg['slippage']
                    fee=2*max(.35,qty*.0035);borrow=qty*entry*.01/360 if side<0 else 0.
                    net=qty*side*(exit-entry)-fee-borrow;capital+=net;upper=p['holding_minutes_upper']
                    marks=[before,before-fee/2-qty*cfg['slippage'],*[before-fee/2+qty*side*(c-entry) for c in p['closes']],capital]
                    if t:
                        decimal_capital+=decimal_trade(t,cfg,label)
                        for key,value in {**s,**{k:v for k,v in p.items() if k not in ('closes','adverse','favorable')},'quantity':qty,'prior_close':f['prior_close'],'prior_sma':f['prior_sma'],'equity_before':before,'equity_after':capital,'net_pnl':net}.items():
                            if isinstance(value,str) or value is None:
                                check(t[key]==('' if value is None else value),'reconstruction_'+key,context)
                            else:
                                near(t[key],value,'reconstruction_'+key,context)
                        near(t['mae_observed_usd'],min(0.,min(qty*side*(v-entry) for v in p['adverse'])),'reconstruction_mae',context)
                        near(t['mfe_observed_usd'],max(0.,max(qty*side*(v-entry) for v in p['favorable'])),'reconstruction_mfe',context)
        for mark in marks:
            peak=max(peak,mark);dd=max(dd,(peak-mark)/peak);dd_usd=max(dd_usd,peak-mark)
        check(d['eligibility']==reason,'daily_reason',context)
        check((d['conditionally_excluded']=='True')==excluded,'daily_excluded',context)
        near(d['quantity'],qty,'daily_quantity',context,0)
        near(d['net_pnl'],net,'daily_pnl',context)
        near(d['equity'],capital,'daily_equity',context)
        near(d['observed_close_drawdown_pct_so_far'],dd*100,'daily_drawdown',context)
        near(d['holding_minutes_upper'],upper,'daily_holding',context,0)
        near(d['return_net'],net/before if before>0 else 0.,'daily_return',context,1e-12)
        if excluded:
            check(d['observed_return']=='','excluded_observation',context)
    check(traded==len(trades),'trade_count',label)
    near(decimal_capital,capital,'full_decimal_account',label)
    near(summary['final_equity'],capital,'summary_equity',label)
    near(summary['net_pnl'],capital-cfg['initial_capital'],'summary_net',label)
    near(summary['observed_close_drawdown_pct'],dd*100,'summary_event_dd',label)
    near(summary['observed_close_drawdown_usd'],dd_usd,'summary_event_dd_usd',label)
    pnls=[float(t['net_pnl']) for t in trades];wins=[x for x in pnls if x>0];losses=[x for x in pnls if x<0]
    near(summary['win_rate_pct'],100*len(wins)/len(pnls) if pnls else None,'summary_win',label)
    near(summary['profit_factor'],math.fsum(wins)/-math.fsum(losses) if losses else None,'summary_pf',label)
    daily_peak=cfg['initial_capital'];daily_dd=0.
    for d in daily:
        value=float(d['equity']);daily_peak=max(daily_peak,value);daily_dd=max(daily_dd,1-value/daily_peak)
    near(summary['max_daily_close_drawdown_pct'],100*daily_dd,'summary_daily_dd',label)
    for key in ('price_move_pnl','friction_cost','commission','borrow_fee'):
        near(summary[key],math.fsum(float(t[key]) for t in trades),'summary_'+key,label)
    near(summary['regular_time_exposure_upper_pct'],100*sum(int(d['holding_minutes_upper']) for d in daily)/sum(int(d['session_minutes']) for d in daily),'summary_exposure',label)
    check(summary['data_excluded_sessions']==sum(d['conditionally_excluded']=='True' for d in daily),'summary_excluded',label)
    check(summary['unresolved_sessions']==len(unresolved),'summary_unresolved',label)
    return dict(label=label,trades=len(trades),daily_rows=len(daily),independent_final_equity=capital,decimal_final_equity=str(decimal_capital),unresolved=len(unresolved))


def original_page_samples(markets,validation):
    results=[]
    for acquisition in validation['acquisitions']:
        manifest=json.loads(Path(acquisition['manifest']).read_text())
        symbol=manifest['symbol'];market=markets[symbol]
        indices={str(x.date()):i for i,x in enumerate(market.dates)}
        count=0
        for page in [manifest['pages'][0],manifest['pages'][-1]]:
            path=Path(page['path'])
            if not path.is_absolute():
                path=ROOT.parents[2]/path
            raw=path.read_bytes()
            check(hashlib.sha256(raw).hexdigest()==page['sha256'],'raw_page_hash',str(path))
            data=json.loads(gzip.decompress(raw));candidates=[]
            for bar in data['bars']:
                stamp=pd.Timestamp(bar['t']);date=str(stamp.tz_convert('America/New_York').date());i=indices.get(date)
                if i is None:
                    continue
                opening=pd.Timestamp(market.quality.iloc[i].session_open)
                slot=int((stamp-opening).total_seconds()/60)
                if 0<=slot<int(market.lengths[i]) and stamp==opening+pd.Timedelta(minutes=slot):
                    candidates.append((bar,i,slot))
            selected=candidates[::max(1,len(candidates)//40)][:40]
            for bar,i,slot in selected:
                for key,raw_key in [('open','o'),('high','h'),('low','l'),('close','c'),('volume','v')]:
                    near(market.arrays[key][i,slot],bar[raw_key],'original_raw_'+key,f'{symbol}/{bar["t"]}',1e-9)
                count+=1
        results.append(dict(symbol=symbol,manifest=acquisition['manifest'],original_pages=2,sampled_rth_minutes=count))
    return results


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--results',type=Path,required=True);args=parser.parse_args()
    out=args.results.resolve()
    if not (out/'RUN_COMPLETE.json').is_file():
        raise SystemExit('Wait for RUN_COMPLETE.json before this independent financial audit')
    frozen=json.loads((out/'PRE_EXECUTION_PROTOCOL.json').read_text())
    spec=importlib.util.spec_from_file_location('independent_source_loader',ROOT.parent/'closing-momentum/scripts/run_study.py')
    source=importlib.util.module_from_spec(spec);sys.modules[spec.name]=source;spec.loader.exec_module(source)
    markets,cash,_=source.load_sources()
    print('Local sources revalidated; independent feature reconstruction',flush=True)
    features={symbol:independent_features(market,cash[symbol]) for symbol,market in markets.items()}
    summaries=[]
    for folder in sorted(p for p in out.iterdir() if p.is_dir() and (p/'summary.json').is_file()):
        summary=json.loads((folder/'summary.json').read_text());cfg=frozen['specifications'][summary['variant']]
        summaries.append(scenario(folder,summary,cfg,features[summary['symbol']],markets[summary['symbol']]))
        print(f'{len(summaries):02d}/72 independently audited {folder.name}',flush=True)
    check(len(summaries)==72,'scenario_count',str(out))
    for symbol,fs in features.items():
        exported=rows(out/f'{symbol}_features_quality.csv')
        check(len(exported)==len(fs),'feature_count',symbol)
        for f,row in zip(fs,exported):
            context=f'{symbol}/{f["date"]}'
            for key in ('prior_close','prior_sma','trend'):
                near(row[key] if row[key] else math.nan,f[key],'feature_'+key,context)
            check(row['regime_reason']==f['regime_reason'],'feature_regime',context)
            reason,s=setup(f,frozen['specifications']['reference'])
            check(row['principal_reason']==reason,'feature_signal_reason',context)
            if s:
                for key,value in s.items():
                    near(row['principal_'+key],value,'feature_signal_'+key,context)
    validation=json.loads((ROOT.parent/'intraday-momentum-noise-area/data/prepared/DATA_VALIDATION.json').read_text())
    samples=original_page_samples(markets,validation)
    report=dict(status='passed' if not failures else 'failed',utc=datetime.now(timezone.utc).isoformat(),results=out.name,method='Independent Python math and Decimal; no strategy or analysis helper called; legacy loader only retrieves/verifies sources.',scenario_count=len(summaries),trade_rows=sum(s['trades'] for s in summaries),daily_rows=sum(s['daily_rows'] for s in summaries),checks=dict(checks),maximum_absolute_errors=dict(max_errors),failure_counts=dict(failure_counts),failures=failures,scenarios=summaries,source_samples=samples,caveats=['Conditional accounts retain the study quality exclusions; unresolved trades are omitted as documented.','Raw samples validate twelve original acquisition pages, not every provider observation.','This audit checks implementation and arithmetic, not economic validity or a fresh out-of-sample claim.'])
    dest=ROOT/'audit'/'AUDIT_RESULTS.json';dest.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('status','scenario_count','trade_rows','daily_rows')})+'; '+str(dest),flush=True)
    if failures:
        print(json.dumps(failures[:10],ensure_ascii=False,indent=2));raise SystemExit(1)


if __name__=='__main__':
    main()
