"""Independent, read-only result audit. Never imports the strategy or its metrics.

The only writes are JSON evidence beside this script. Source CSV remains local.
"""
from collections import Counter
import csv
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
import gzip
import hashlib
import json
import math
from pathlib import Path
from statistics import NormalDist
import subprocess
from zoneinfo import ZoneInfo

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'results/2026-10-24-python-v1'
NY = ZoneInfo('America/New_York')
D = Decimal
errors = []
checks = Counter()
max_deltas = Counter()


def check(ok, label, context=''):
    checks[label] += 1
    if not ok and len(errors) < 100:
        errors.append({'check': label, 'context': str(context)})


def near(actual, expected, label, context='', atol=1e-7, rtol=1e-10):
    delta = abs(float(actual) - float(expected))
    max_deltas[label] = max(max_deltas[label], delta)
    check(delta <= atol + rtol * abs(float(expected)), label,
          f'{context}: actual={actual} expected={expected} delta={delta}')


def records(path):
    with path.open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def truth(value):
    return value is True or str(value).lower() == 'true'


def allowed(ts):
    dt = datetime.fromtimestamp(int(ts), NY)
    return 2 <= dt.hour < 8


def independent_bars(t, bid):
    bucket = t // 900 * 900
    first = np.r_[0, np.flatnonzero(bucket[1:] != bucket[:-1]) + 1]
    count = np.diff(np.r_[first, len(t)])
    bars = {'t': bucket[first], 'o': bid[first, 0],
            'h': np.maximum.reduceat(bid[:, 1], first),
            'l': np.minimum.reduceat(bid[:, 2], first),
            'c': bid[first + count - 1, 3], 'complete': count == 15}
    pivots = {'h': [], 'l': []}
    for k in range(10, len(first)):
        if not bars['complete'][k-10:k+1].all() or bars['t'][k] - bars['t'][k-10] != 9000:
            continue
        mid = k - 5
        for side in ('h', 'l'):
            values = bars[side]
            centre = values[mid]
            if side == 'h':
                ok = centre >= max(values[k-10:mid]) and centre > max(values[mid+1:k+1])
            else:
                ok = centre <= min(values[k-10:mid]) and centre < min(values[mid+1:k+1])
            if ok:
                pivots[side].append((k, int(centre), mid))
    return bars, pivots


def ema_feature_audit(pair,t,bid,bars):
    hour = t//3600*3600
    first = np.r_[0,np.flatnonzero(hour[1:]!=hour[:-1])+1]
    count = np.diff(np.r_[first,len(t)])
    full = count==60
    hour_end = hour[first[full]]+3600
    hour_close = bid[(first+count-1)[full],3]
    directions = [0]
    fast = slow = float(hour_close[0])
    for price in hour_close[1:]:
        fast = fast*(1-2/51)+float(price)*(2/51)
        slow = slow*(1-2/201)+float(price)*(2/201)
        directions.append(1 if fast>slow else -1 if fast<slow else 0)
    latest = np.searchsorted(hour_end,bars['t']+900,side='right')-1
    expected = np.zeros(len(latest),dtype=np.int8)
    ready = latest>=199
    ready &= bars['t']+900-hour_end[np.maximum(latest,0)]<3600
    expected[ready] = np.array(directions,dtype=np.int8)[latest[ready]]
    mismatches = []
    path = ROOT/'data/prepared'/f'{pair}_features.csv.gz'
    with gzip.open(path,'rt',encoding='utf-8',newline='') as handle:
        rows = 0
        for k,row in enumerate(csv.DictReader(handle)):
            if int(row['t'])!=bars['t'][k] or int(row['trend_b'])!=expected[k]:
                if len(mismatches)<10:
                    mismatches.append({'bar':k,'time':row['t'],'actual':row['trend_b'],'expected':int(expected[k])})
            rows += 1
    check(rows==len(bars['t']) and not mismatches,'EMA_all_features_independent_complete_hour_causality',
          f'{pair}: {mismatches}')
    return {'features_checked':rows,'complete_hours':len(hour_close),'bars_after_200_hour_warmup':int(ready.sum()),
            'mismatches':mismatches,'feature_file_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def financial_audit(folder, t, bid, config):
    summary = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))
    state = json.loads((folder / 'end_state.json').read_text(encoding='utf-8'))
    trades = records(folder / 'trades.csv')
    setups = records(folder / 'setups.csv')
    scale = D(1000 if summary['pair'] == 'USDJPY' else 100000)
    cost = D(str(config['cost_pips']))
    balance = D(100000)
    nets, rs = [], []
    peak_equity = 100000.0
    max_equity_dd = 0.0
    numeric_qty_rounding = 0

    def mark(equity):
        nonlocal peak_equity, max_equity_dd
        equity = float(equity)
        peak_equity = max(peak_equity, equity)
        max_equity_dd = max(max_equity_dd, (peak_equity-equity)/peak_equity)

    previous_exit = -1
    for row in trades:
        context = f'{folder.relative_to(RUN)} setup={row["setup_index"]}'
        qty, side = D(row['qty']), int(row['d'])
        entry, stop, exit_price = int(row['entry_ticks']), int(row['sl']), int(row['exit_ticks'])
        distance = side * (entry-stop)
        gross = qty * side * (exit_price-entry) / scale
        fee = qty * D(10) * cost / scale
        net = gross-fee
        risk = qty * distance / scale
        expected_qty = int((balance * D('.01') / (D(distance)/scale)).to_integral_value(rounding=ROUND_FLOOR))
        qty_diff = abs(int(qty)-expected_qty)
        check(qty_diff <= 1, 'frozen_1pct_quantity_decimal', context)
        numeric_qty_rounding += qty_diff != 0
        check(int(row['entry_time']) >= previous_exit, 'positions_do_not_overlap', context)
        check(qty*entry/scale <= balance*100,'entry_margin_100x_cap',context)
        previous_exit = int(row['exit_time'])
        near(row['holding_minutes'],(int(row['exit_time'])-int(row['entry_time']))/60,
             'trade_holding_minutes',context)
        for key, expected in [('gross_pnl',gross), ('commission',fee), ('net_pnl',net),
                              ('risk_cash',risk), ('net_r',net/risk)]:
            near(D(row[key]), expected, 'trade_'+key, context)
        balance -= fee/2
        mark(balance)
        ia, ib = np.searchsorted(t, [int(row['entry_time']), int(row['exit_time'])])
        check(ia < len(t) and ib < len(t) and t[ia] == int(row['entry_time']) and t[ib] == int(row['exit_time']),
              'trade_timestamps_are_source_minutes', context)
        if ia < ib:
            equities = float(balance) + float(qty)*side*(bid[ia:ib,3]-entry)/float(scale)
            running_peak = np.maximum.accumulate(np.r_[peak_equity, equities])[1:]
            max_equity_dd = max(max_equity_dd, float(np.max((running_peak-equities)/running_peak)))
            peak_equity = max(peak_equity, float(equities.max()))
        balance += gross-fee/2
        mark(balance)
        near(D(row['ending_balance']),balance,'trade_ending_balance',context)
        nets.append(net)
        rs.append(net/risk)
    open_position = state['open_position']
    equity = balance
    if open_position:
        qty, side = D(str(open_position['qty'])), open_position['d']
        balance -= qty*D(10)*cost/scale/2
        mark(balance)
        ia = int(np.searchsorted(t,open_position['entry_time']))
        values = float(balance)+float(qty)*side*(bid[ia:,3]-open_position['entry'])/float(scale)
        running_peak = np.maximum.accumulate(np.r_[peak_equity,values])[1:]
        max_equity_dd = max(max_equity_dd,float(np.max((running_peak-values)/running_peak)))
        equity = balance+qty*side*(int(bid[-1,3])-open_position['entry'])/scale
    wins = sum(x>0 for x in nets)
    losses = -sum((x for x in nets if x<0),D(0))
    gains = sum((x for x in nets if x>0),D(0))
    resolved = [r for r in trades if r['exit_reason']!='COVERAGE_GAP_STOP' and not truth(r['crossed_gap'])]
    penalties = [r for r in trades if r['exit_reason']=='COVERAGE_GAP_STOP']
    for key, expected in [('closed_trades',len(trades)), ('wins',wins), ('resolved_closed_trades',len(resolved)),
                          ('coverage_penalty_trades',len(penalties)),('long_trades',sum(int(r['d'])==1 for r in trades)),
                          ('short_trades',sum(int(r['d'])==-1 for r in trades)),
                          ('ambiguous_front_run_trades',sum(truth(r['ambiguous_front_run']) for r in trades)),
                          ('dual_touch_trades',sum(truth(r['dual_touch']) for r in trades)),
                          ('crossed_gap_trades',sum(truth(r['crossed_gap']) for r in trades)),
                          ('overnight_24h_trades',sum(D(r['holding_minutes'])>=1440 for r in trades))]:
        check(summary[key]==expected,'summary_'+key,str(folder))
    check(summary['minimum_100_resolved']==(len(resolved)>=100),'minimum_100_resolved',str(folder))
    check(summary['open_position_end']==(open_position is not None),'summary_open_position_flag',str(folder))
    top3 = sum(sorted((v for v in nets if v>0),reverse=True)[:3],D(0))
    for key,expected in [('net_pnl',sum(nets,D(0))),('commission',sum((D(r['commission']) for r in trades),D(0))),
                         ('gross_pnl',sum((D(r['gross_pnl']) for r in trades),D(0))),('ending_balance',balance),
                         ('ending_equity',equity),('sum_r',sum(rs,D(0))),('max_marked_dd_pct',max_equity_dd*100),
                         ('return_pct',100*(equity/D(100000)-1)),('top3_positive_pnl',top3),
                         ('net_less_top3_cash_diagnostic',sum(nets,D(0))-top3),
                         ('coverage_penalty_net_pnl',sum((D(r['net_pnl']) for r in penalties),D(0))),
                         ('resolved_only_net_pnl_diagnostic',sum((D(r['net_pnl']) for r in resolved),D(0)))]:
        near(summary[key],expected,'summary_'+key,str(folder))
    a = datetime(2020 if summary['period']=='B' else 2015,1,1,tzinfo=timezone.utc)
    b = datetime(2020 if summary['period']=='A' else 2025,1,1,tzinfo=timezone.utc)
    years = (b-a).total_seconds()/86400/365.2425
    if equity>0:
        near(summary['cagr_pct'],100*((float(equity)/100000)**(1/years)-1),'summary_fixed_window_CAGR',str(folder))
    cumulative = peak = dd = D(0)
    streak = longest = 0
    for value in rs:
        cumulative += value
        peak = max(peak,cumulative)
        dd = max(dd,peak-cumulative)
        streak = streak+1 if value<0 else 0
        longest = max(longest,streak)
    near(summary['max_closed_dd_r'],dd,'summary_closed_R_drawdown',str(folder))
    check(summary['longest_loss_streak']==longest,'summary_loss_streak',str(folder))
    if trades:
        near(summary['expectancy_r'],sum(rs,D(0))/len(rs),'summary_expectancy_r',str(folder))
        near(summary['win_rate_pct'],100*wins/len(trades),'summary_win_rate',str(folder))
        n = len(trades)
        z = NormalDist().inv_cdf(.975)
        p = wins/n
        denominator = 1+z*z/n
        centre = (p+z*z/(2*n))/denominator
        half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denominator
        near(summary['wilson_low_pct'],100*(centre-half),'summary_Wilson_lower',str(folder))
        near(summary['wilson_high_pct'],100*(centre+half),'summary_Wilson_upper',str(folder))
    if losses:
        near(summary['profit_factor'],gains/losses,'summary_profit_factor',str(folder))
    statuses = Counter(r['status'].upper() for r in setups)
    for reason in ('front_run','gap','expiry','session'):
        check(summary['cancel_'+reason]==statuses['CANCEL_'+reason.upper()], 'setup_cancel_counter_'+reason,str(folder))
    check(statuses['CLOSED']==len(trades),'setup_closed_counter',str(folder))
    check(summary['front_run_ambiguous_setups']==sum(truth(r['ambiguous_front_run']) for r in setups),
          'setup_ambiguous_counter',str(folder))
    if summary['variant'] in ('reference','fill_first','observed_gap'):
        check(summary['candidate_nowicks']==len(setups)+summary['reject_stop']+summary['reject_margin'],
              'candidate_reconciliation_unfiltered_structure',str(folder))
    return {'pair':summary['pair'],'period':summary['period'],'variant':summary['variant'],
            'closed':len(trades),'resolved':len(resolved),'penalties':len(penalties),
            'independent_net_pnl':str(sum(nets,D(0))),'independent_marked_dd_pct':max_equity_dd*100,
            'quantity_float_floor_differences_of_one_unit':numeric_qty_rounding,
            'cross_NY_calendar_date_trades':sum(datetime.fromtimestamp(int(r['entry_time']),NY).date()!=datetime.fromtimestamp(int(r['exit_time']),NY).date() for r in trades)}, trades, setups


def causal_audit(trades,setups,t,bid,bars,pivots,mode):
    indices = {int(ts):i for i,ts in enumerate(bars['t'])}
    hi_indices = np.array([p[0] for p in pivots['h']])
    lo_indices = np.array([p[0] for p in pivots['l']])
    by_setup = {int(r['setup_index']):r for r in setups}
    trades_by_setup = {int(r['setup_index']):r for r in trades}
    for row in setups:
        signal = int(row['signal_time'])
        k = indices[signal-900]
        side = int(row['d'])
        e,sl,tp,extreme,pivot = map(lambda key:int(row[key]),['entry','sl','tp','extreme','pivot'])
        context = f'{mode} setup={row["setup_index"]} signal={signal}'
        check(k==int(row['signal_bar']) and bars['complete'][k],'signal_15m_complete_index',context)
        check(allowed(signal),'signal_next_minute_NY_window',context)
        check(e==bars['o'][k] and (bars['o'][k]==bars['l'][k] and bars['c'][k]>bars['o'][k] if side==1 else bars['o'][k]==bars['h'][k] and bars['c'][k]<bars['o'][k]),
              'signal_zero_tolerance_nowick',context)
        nh = int(np.searchsorted(hi_indices,k,side='right'))
        nl = int(np.searchsorted(lo_indices,k,side='right'))
        check(nh>=2 and nl>=2,'structure_two_confirmed_pivots_each_side',context)
        if nh>=2 and nl>=2:
            h0,h1 = pivots['h'][nh-2][1],pivots['h'][nh-1][1]
            l0,l1 = pivots['l'][nl-2][1],pivots['l'][nl-1][1]
            check((h1>h0 and l1>l0) if side==1 else (h1<h0 and l1<l0),'structure_direction_confirmed_at_signal',context)
            check(pivot==(l1 if side==1 else h1),'stop_uses_last_known_opposite_pivot',context)
        check(sl==pivot-side*30 and 50<=side*(e-sl)<=300 and tp==e+side*side*(e-sl),
              'frozen_stop_buffer_bounds_1R',context)
        check(extreme==bars['h' if side==1 else 'l'][k],'signal_front_run_extreme',context)
        # Replay each accepted order, including cancellations, independently of
        # exported trade existence. An accepted order cannot disappear silently.
        terminal = None
        ambiguous = False
        filled_at = None
        for future in range(k+1,min(k+11,len(bars['t']))):
            bt = int(bars['t'][future])
            if not allowed(bt):
                terminal = 'CANCEL_SESSION'
                break
            ia,iz = np.searchsorted(t,[bt,bt+900])
            for j in range(ia,iz):
                if j>0 and t[j]-t[j-1]>60:
                    terminal = 'CANCEL_GAP'
                    break
                o,h,l,c = map(int,bid[j])
                if side*(o-extreme)>0:
                    terminal = 'CANCEL_FRONT_RUN'
                elif side*(e-o)>=10:
                    terminal,filled_at = 'FILL',int(t[j])
                else:
                    hit = l<=e-10 if side==1 else h>=e+10
                    breach = h>extreme if side==1 else l<extreme
                    ambiguous = hit and breach
                    if breach and (not hit or mode=='cancel_first'):
                        terminal = 'CANCEL_FRONT_RUN'
                    elif hit:
                        terminal,filled_at = 'FILL',int(t[j])
                if terminal:
                    break
            if terminal:
                break
            if future-k>=9:
                terminal = 'CANCEL_EXPIRY'
                break
            if not allowed(bt+900):
                terminal = 'CANCEL_SESSION'
                break
        exported_status = row['status'].upper()
        if terminal=='FILL':
            check(exported_status in ['CLOSED','FILLED'],'accepted_order_fill_status',context)
            if int(row['setup_index']) in trades_by_setup:
                check(int(trades_by_setup[int(row['setup_index'])]['entry_time'])==filled_at,
                      'accepted_order_fill_time',context)
        else:
            check(exported_status==(terminal or 'OPEN_PENDING_END'),'accepted_order_cancellation_reason',
                  f'{context} exported={exported_status} independent={terminal}')
        check(truth(row['ambiguous_front_run'])==ambiguous,'accepted_order_ambiguity_flag',context)
    for row in trades:
        side,e,sl,tp = (int(row[x]) for x in ['d','entry_ticks','sl','tp'])
        context = f'{mode} trade={row["setup_index"]}'
        signal = int(row['signal_time'])
        ia,ib,ic = np.searchsorted(t,[signal,int(row['entry_time']),int(row['exit_time'])])
        signal_k = int(row['signal_bar'])
        entry_k = indices[int(t[ib]//900*900)]
        check(1<=entry_k-signal_k<=9,'entry_within_nine_following_bars',context)
        check(allowed(t[ib]),'entry_NY_0200_0800_DST',context)
        check(t[ib]>=signal,'entry_after_completed_signal',context)
        check(np.all(np.diff(t[ia-1:ib+1])==60),'pending_no_source_gap',context)
        extreme = int(row['extreme'])
        first_fill = None
        for j in range(ia,ib+1):
            o,h,l,c = map(int,bid[j])
            open_front = side*(o-extreme)>0
            at_open = side*(e-o)>=10
            hit = l<=e-10 if side==1 else h>=e+10
            breached = h>extreme if side==1 else l<extreme
            event = 'cancel' if open_front else 'fill' if at_open else 'cancel' if breached and (not hit or mode=='cancel_first') else 'fill' if hit else 'wait'
            check(event!='cancel','pending_no_prior_front_run_cancellation',context)
            if event=='fill':
                first_fill = j
                break
        check(first_fill==ib,'entry_first_eligible_minute_penetration',context)
        entry_at_open = side*(e-int(bid[ib,0]))>=10
        check(entry_at_open==truth(row['entry_at_open']),'entry_open_known_flag',context)
        found = None
        crossed_gap = False
        for j in range(ib,ic+1):
            o,h,l,c = map(int,bid[j])
            gap = j>0 and t[j]-t[j-1]>60
            if gap:
                crossed_gap = True
                found = (j,min(sl,o) if side==1 else max(sl,o),'COVERAGE_GAP_STOP')
                break
            intramin = j==ib and not entry_at_open
            if not intramin and side*(o-sl)<=0:
                found = (j,o,'SL_GAP' if o!=sl else 'SL')
            elif not intramin and side*(o-tp)>=10:
                found = (j,tp,'TP')
            elif (l<=sl if side==1 else h>=sl):
                found = (j,sl,'SL')
            elif (h>=tp+10 if side==1 else l<=tp-10) and (not intramin or side*(c-tp)>=10):
                found = (j,tp,'TP')
            if found:
                break
        check(found==(ic,int(row['exit_ticks']),row['exit_reason']),'exit_first_minute_SL_TP_gap_priority',context)
        check(crossed_gap==truth(row['crossed_gap']),'exit_gap_flag',context)
    return {'accepted_setups':len(setups),'closed_trades':len(trades),'mode':mode}


def source_audit(pair,raw_t,raw_bid,raw_ask,trades,manifest):
    samples = []
    cache = {}
    candidates = [r for r in manifest['archives'] if r['pair']==pair and r['status']==200]
    scale = D(1000 if pair=='USDJPY' else 100000)
    selected = []
    if trades:
        selected = [trades[0],trades[len(trades)//2],trades[-1]]
        selected += [next((r for r in trades if r['exit_reason']==reason),trades[0]) for reason in ['TP','COVERAGE_GAP_STOP']]
    for row in selected:
        for event,ts in [('signal_open',int(row['signal_time'])-900),('entry',int(row['entry_time'])),('exit',int(row['exit_time']))]:
            dt = datetime.fromtimestamp(ts,timezone.utc)
            text_time = dt.strftime('%m/%d/%Y %H:%M:%S')+'.000'
            week = dt.isocalendar().week
            likely = [r for r in candidates if abs(r['year']-dt.year)<=1 and (abs(r['week']-week)<=2 or week in [1,52,53] and r['week'] in [1,2,51,52,53])]
            matched = None
            for rec in likely:
                path = ROOT/rec['path']
                if str(path) not in cache:
                    blob = path.read_bytes()
                    check(hashlib.sha256(blob).hexdigest()==rec['sha256'],'raw_archive_SHA256',rec['path'])
                    cache[str(path)] = {r['DateTime']:r for r in csv.DictReader(gzip.decompress(blob).decode('utf-8-sig').splitlines())}
                if text_time in cache[str(path)]:
                    matched = (rec,cache[str(path)][text_time])
                    break
            check(matched is not None,'original_csv_timestamp_found',f'{pair} {text_time}')
            if matched is None:
                continue
            rec,original = matched
            j = int(np.searchsorted(raw_t,ts))
            values = [int(D(original[key])*scale) for key in ['BidOpen','BidHigh','BidLow','BidClose','AskOpen','AskHigh','AskLow','AskClose']]
            check(values==list(map(int,raw_bid[j]))+list(map(int,raw_ask[j])),'original_csv_matches_prepared_8_OHLC',f'{pair} {text_time}')
            samples.append({'pair':pair,'event':event,'timestamp_utc':dt.isoformat(),'archive':rec['path'],
                            'archive_sha256':rec['sha256'],'ticks_8_OHLC':values})
    return samples


def main():
    run_manifest = json.loads((RUN/'RUN_MANIFEST.json').read_text(encoding='utf-8'))
    source_manifest_path = ROOT/'results/2026-10-24-python/source_manifest.json'
    source_manifest = json.loads(source_manifest_path.read_text(encoding='utf-8'))
    check(hashlib.sha256(source_manifest_path.read_bytes()).hexdigest()==run_manifest['source_manifest_sha256'],
          'run_source_manifest_SHA256')
    for relative,expected_hash in run_manifest['code_sha256'].items():
        snapshot = RUN/'code_snapshot'/relative
        check(snapshot.exists() and hashlib.sha256(snapshot.read_bytes()).hexdigest()==expected_hash,
              'immutable_code_snapshot_SHA256',relative)
    dependency = json.loads((RUN/'DEPENDENCY_PROVENANCE.json').read_text(encoding='utf-8'))
    for path in [ROOT/dependency['dependency'],RUN/'code_snapshot'/dependency['dependency']]:
        check(hashlib.sha256(path.read_bytes()).hexdigest()==dependency['snapshot_sha256'],
              'supplementary_reference_dependency_SHA256',str(path))
    blob = subprocess.run(['git','show',dependency['original_commit']+':studies/nowick-compensation/reference.py'],
                          cwd=ROOT.parents[1],capture_output=True,check=True).stdout
    check(hashlib.sha256(blob).hexdigest()==dependency['original_git_blob_sha256'],
          'supplementary_reference_original_Git_blob_SHA256')
    financial, causal, source_samples, ema = [], {}, [], {}
    summaries = sorted(RUN.glob('*/*/*/summary.json'))
    for pair in ['GBPUSD','USDJPY','AUDUSD']:
        pair_summaries = [p for p in summaries if p.parts[-4]==pair]
        if not pair_summaries:
            continue
        prepared = ROOT/'data/prepared'/f'{pair}_m1.npz'
        check(hashlib.sha256(prepared.read_bytes()).hexdigest()==source_manifest['prepared'][pair]['sha256'],
              'prepared_SHA256',pair)
        with np.load(prepared,allow_pickle=False) as raw:
            raw_t,raw_bid,raw_ask = raw['t'],raw['bid'],raw['ask']
            valid = raw['valid_bid']
            valid_ask = raw['valid_ask']
        check(np.all(np.diff(raw_t)>0) and np.all(raw_t%60==0),'prepared_unique_minute_chronology',pair)
        for side,quotes,flags in [('bid',raw_bid,valid),('ask',raw_ask,valid_ask)]:
            expected = (quotes>0).all(axis=1)&(quotes[:,1]>=np.maximum(quotes[:,0],quotes[:,3]))&(quotes[:,2]<=np.minimum(quotes[:,0],quotes[:,3]))
            check(np.array_equal(expected,flags),'prepared_'+side+'_OHLC_validity_flags',pair)
        t,bid = raw_t[valid],raw_bid[valid]
        bars,pivots = independent_bars(t,bid)
        ema[pair] = ema_feature_audit(pair,t,bid,bars)
        for path in pair_summaries:
            config = run_manifest['configs'][path.parent.name]
            result,trades,setups = financial_audit(path.parent,t,bid,config)
            financial.append(result)
            if path.parts[-3]=='ALL' and path.parent.name in ['reference','fill_first']:
                mode = 'cancel_first' if path.parent.name=='reference' else 'fill_first'
                causal[pair+'/'+path.parent.name] = causal_audit(trades,setups,t,bid,bars,pivots,mode)
                if path.parent.name=='reference':
                    source_samples += source_audit(pair,raw_t,raw_bid,raw_ask,trades,source_manifest)
        print(pair, 'audited summaries',len(pair_summaries),'errors so far',len(errors),flush=True)
    if run_manifest['complete']:
        check(len(financial)==126,'complete_run_has_126_independent_summaries')
        comparison = records(RUN/'comparison_all.csv')
        keys = [(r['pair'],r['period'],r['variant']) for r in comparison]
        check(len(keys)==126 and len(set(keys))==126,'comparison_has_126_unique_rows')
        for row in comparison:
            summary = json.loads((RUN/row['pair']/row['period']/row['variant']/'summary.json').read_text(encoding='utf-8'))
            for key,expected in summary.items():
                if expected is None:
                    check(row[key]=='','comparison_null_value',key)
                elif isinstance(expected,bool):
                    check(truth(row[key])==expected,'comparison_boolean_value',key)
                elif isinstance(expected,(int,float)):
                    near(row[key],expected,'comparison_numeric_value',key)
                else:
                    check(row[key]==expected,'comparison_text_value',key)
        minimum = json.loads((RUN/'MINIMUM_100.json').read_text(encoding='utf-8'))
        bases = [r for r in financial if r['period']=='ALL' and r['variant']=='reference']
        check(len(bases)==3,'minimum_three_distinct_pair_references')
        check(minimum['all_three_pass']==all(r['resolved']>=100 for r in bases),'minimum100_all_three_flag')
        for row in bases:
            declared = minimum['pairs'][row['pair']]
            check(declared['closed_trades']==row['closed'] and declared['resolved_closed_trades']==row['resolved']
                  and declared['minimum_100_resolved']==(row['resolved']>=100),'minimum100_distinct_pair_counts',row['pair'])
    evidence = {'created_utc':datetime.now(timezone.utc).isoformat(),'run':RUN.name,'run_complete_at_audit':run_manifest['complete'],
                'audit_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'independence':'No imports from fx_engine, fx_metrics, fx_data or reference. Decimal cash arithmetic; math/NormalDist Wilson; independent source-minute and pivot reconstruction.',
                'checks':dict(checks),'max_numeric_deltas':dict(max_deltas),'errors':errors,'financial_audits':financial,
                'causal_audits':causal,'EMA_complete_history_audits':ema,'original_csv_samples':source_samples,
                'limitations':['Audits exported trades and accepted setups; does not independently enumerate all possible rejected signal candidates.',
                               'Minute OHLC cannot establish actual tick order; checks the declared deterministic ambiguity policies.',
                               'Source CSV samples verify provenance/transform, not FXCM quote accuracy.']}
    output = Path(__file__).with_name('independent_audit_v1.json')
    output.write_text(json.dumps(evidence,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    print('Audit:',len(financial),'summaries;',sum(checks.values()),'checks;',len(errors),'errors;',output,flush=True)
    if errors:
        print(json.dumps(errors[:10],indent=2))
        raise SystemExit(1)


if __name__=='__main__':
    main()
