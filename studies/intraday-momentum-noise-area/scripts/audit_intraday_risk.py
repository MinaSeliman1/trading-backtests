"""Audit indépendant des trajectoires archivées, sans recalcul de signaux.

Exemple : python scripts/audit_intraday_risk.py --results results/2026-10-19
    --prepared data/prepared

Le DD utilise exactement les marques comptables annoncées : closes des minutes
détenues, marque à la référence après entrée, solde après sortie et coûts. La
durée commence au dernier sommet avant le creux et finit à la récupération ou
à la dernière observation, avec censure explicite. Le maximum de levier ajoute
les prix de référence et de fill aux exécutions ; ces observations ont un poids
temporel nul. Sa moyenne est une quadrature à droite, une observation par minute
détenue. Aucune information high/low, tick ou trajectoire intrabar n'est inférée.
Les CSV/JSON d'origine restent inchangés ; seuls INTRADAY_RISK_AUDIT.csv/.json
sont produits dans le dossier de résultats (ou --out).
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import argparse
from datetime import datetime, timezone
import hashlib
import json
import pickle

import numpy as np
import pandas as pd


MINUTE_NS = 60_000_000_000
DAY_NS = 86_400_000_000_000
USD_TOLERANCE = 1e-5


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def timestamp(nanoseconds):
    return str(pd.Timestamp(int(nanoseconds), tz='UTC').tz_convert('America/New_York'))


def drawdown_episode(curve, times, percentage):
    peaks = np.maximum.accumulate(curve)
    values = (peaks-curve)/peaks if percentage else peaks-curve
    trough = int(np.argmax(values))
    if values[trough] <= 0:
        return dict(peak_time=None, trough_time=None, recovery_time=None,
                    recovered=None, censored_at=None, duration_calendar_days=0.,
                    duration_calendar_dates=0)
    # A flat high-water plateau ends at its last mark, not its first occurrence.
    peak = int(np.flatnonzero(curve[:trough+1] == peaks[trough])[-1])
    recovery = np.flatnonzero(curve[trough+1:] >= peaks[trough])
    end = int(trough+1+recovery[0]) if len(recovery) else len(curve)-1
    peak_time = pd.Timestamp(int(times[peak]), tz='UTC').tz_convert('America/New_York')
    end_time = pd.Timestamp(int(times[end]), tz='UTC').tz_convert('America/New_York')
    return dict(peak_time=timestamp(times[peak]), trough_time=timestamp(times[trough]),
                recovery_time=timestamp(times[end]) if len(recovery) else None,
                recovered=bool(len(recovery)), censored_at=None if len(recovery) else timestamp(times[end]),
                duration_calendar_days=float((times[end]-times[peak])/DAY_NS),
                duration_calendar_dates=(end_time.date()-peak_time.date()).days)


def audit_frames(market, trades, daily, summary):
    """Rebuild account marks from raw bars and archived order fills only."""
    assert len(daily) and daily.date.is_unique, 'empty or duplicate daily dates'
    assert daily.date.is_monotonic_increasing, 'daily dates out of order'
    assert set(trades.date).issubset(set(daily.date)), 'trade outside audited period'
    day_index = {str(day.date()): i for i, day in enumerate(market.dates)}
    groups = {day: frame for day, frame in trades.groupby('date', sort=False)}
    curve_chunks = []; time_chunks = []; errors = []
    capital = 100000.; peak = capital; max_dd_usd = 0.; max_dd_fraction = 0.
    total_net = 0.; holding_minutes = 0; leverage_sum = 0.
    max_leverage = 0.; max_leverage_time = None; max_leverage_kind = None
    invalid_leverage_marks = 0; invalid_weighted_marks = 0
    slippage = float(summary['slippage']); borrow_rate = float(summary['borrow_rate'])

    def check(actual, expected, label, tolerance=USD_TOLERANCE, ledger=True):
        error = abs(float(actual)-float(expected))
        assert np.isfinite(error) and error <= tolerance, f'{label}: {actual} != {expected}'
        if ledger:
            errors.append(error)

    def exposure(price, equity, clock, kind, weighted=False):
        nonlocal leverage_sum, max_leverage, max_leverage_time, max_leverage_kind
        nonlocal invalid_leverage_marks, invalid_weighted_marks
        prices = np.atleast_1d(price).astype(float)
        equities = np.broadcast_to(np.asarray(equity, dtype=float), prices.shape)
        clocks = np.broadcast_to(np.asarray(clock, dtype=np.int64), prices.shape)
        good = np.isfinite(equities) & (equities > 0)
        invalid_leverage_marks += int((~good).sum())
        if weighted:
            invalid_weighted_marks += int((~good).sum())
        ratios = np.divide(prices, equities, out=np.zeros_like(prices), where=good)
        if weighted:
            leverage_sum += float(ratios.sum())
        if len(ratios) and ratios.max() > max_leverage:
            k = int(np.argmax(ratios)); max_leverage = float(ratios[k])
            max_leverage_time = timestamp(clocks[k]); max_leverage_kind = kind

    for row in daily.itertuples(index=False):
        i = day_index[row.date]; n = int(market.lengths[i])
        assert n == row.session_minutes, f'{row.date}: session length mismatch'
        opening = pd.Timestamp(row.date+' 09:30', tz='America/New_York').value
        closes = market.arrays['close'][i, :n]
        balance = capital; cursor = 0; day_net = 0.; commission = 0.; borrow_total = 0.
        day_values = [np.array([capital])]; day_times = [np.array([opening], dtype=np.int64)]
        group = groups.get(row.date)

        def mark(equity, clocks):
            values = np.atleast_1d(equity).astype(float)
            assert np.isfinite(values).all(), f'{row.date}: invalid account mark'
            day_values.append(values)
            day_times.append(np.broadcast_to(np.asarray(clocks, dtype=np.int64), values.shape))

        def flat_until(until):
            nonlocal cursor
            assert cursor <= until <= n, f'{row.date}: overlapping/out-of-session trades'
            if until > cursor:
                mark(np.full(until-cursor, balance), opening+np.arange(cursor+1, until+1)*MINUTE_NS)
            cursor = until

        if group is not None:
            assert market.valid[i], f'{row.date}: trade on excluded session'
            for trade in group.itertuples(index=False):
                q = int(trade.quantity); sign = int(trade.sign)
                assert q == trade.quantity and q > 0 and sign in (-1, 1), 'invalid quantity/sign'
                check(trade.equity_at_day_start, capital, 'equity at day start')
                phases = (trade.entry_phase, trade.exit_phase)
                assert all(phase in ('open', 'close') for phase in phases), 'invalid execution phase'
                eb = int(trade.entry_bar); xb = int(trade.exit_bar)
                assert 0 <= eb < n and 0 <= xb < n, 'execution outside session'
                start = eb+int(trade.entry_phase == 'close')
                end = xb+int(trade.exit_phase == 'close')
                assert end >= start, 'negative holding period'
                entry_clock = opening+start*MINUTE_NS; exit_clock = opening+end*MINUTE_NS
                assert pd.Timestamp(trade.entry_time).value == entry_clock, 'entry timestamp mismatch'
                assert pd.Timestamp(trade.exit_time).value == exit_clock, 'exit timestamp mismatch'
                entry_ref = float(market.arrays[trade.entry_phase][i, eb])
                exit_ref = float(market.arrays[trade.exit_phase][i, xb])
                check(trade.entry_reference, entry_ref, 'raw entry reference', 1e-9, False)
                check(trade.exit_reference, exit_ref, 'raw exit reference', 1e-9, False)
                entry_fill = entry_ref+sign*slippage; exit_fill = exit_ref-sign*slippage
                check(trade.entry_price, entry_fill, 'entry fill', 1e-9, False)
                check(trade.exit_price, exit_fill, 'exit fill', 1e-9, False)
                fee = max(.35, q*.0035)
                gross = sign*q*(exit_fill-entry_fill)
                borrow = q*entry_fill*borrow_rate/360 if sign < 0 else 0.
                net = gross-2*fee-borrow
                for name, value in [('gross_pnl', gross), ('commission', 2*fee),
                                    ('borrow_fee', borrow), ('net_pnl', net)]:
                    check(getattr(trade, name), value, f'{row.date} trade {name}')
                check(trade.holding_minutes, end-start, 'holding minutes', 1e-8, False)
                flat_until(start)
                balance -= fee
                entry_equity = balance+sign*q*(entry_ref-entry_fill)
                mark(entry_equity, entry_clock)
                exposure(q*entry_ref, entry_equity, entry_clock, 'entry_reference_after_cost')
                exposure(q*entry_fill, balance, entry_clock, 'entry_fill_after_commission')
                if end > start:
                    held_prices = closes[start:end]
                    held_equity = balance+sign*q*(held_prices-entry_fill)
                    held_clocks = opening+np.arange(start+1, end+1)*MINUTE_NS
                    mark(held_equity, held_clocks)
                    exposure(q*held_prices, held_equity, held_clocks, 'held_minute_close', True)
                holding_minutes += end-start
                exposure(q*exit_ref, balance+sign*q*(exit_ref-entry_fill), exit_clock,
                         'exit_reference_before_close')
                exposure(q*exit_fill, balance+gross, exit_clock, 'exit_fill_before_close')
                balance += gross-fee-borrow
                mark(balance, exit_clock); cursor = end
                day_net += net; commission += 2*fee; borrow_total += borrow
        flat_until(n)
        # Explicit final timestamp also covers a session ending with a close fill.
        mark(balance, opening+n*MINUTE_NS)
        values = np.concatenate(day_values); clocks = np.concatenate(day_times)
        assert (np.diff(clocks) >= 0).all(), f'{row.date}: unordered marks'
        check(row.trades, 0 if group is None else len(group), 'daily trade count', 0., False)
        for name, value in [('net_pnl', balance-capital), ('commission', commission),
                            ('borrow_fee', borrow_total), ('equity', balance),
                            ('min_equity', values.min()), ('max_equity', values.max())]:
            check(getattr(row, name), value, f'{row.date} daily {name}')
        check(day_net, balance-capital, 'cash ledger vs trade sum')
        check(row.return_net, (balance-capital)/capital, 'daily return', 1e-10, False)
        peaks = np.maximum.accumulate(np.r_[peak, values])[1:]
        max_dd_usd = max(max_dd_usd, float((peaks-values).max()))
        max_dd_fraction = max(max_dd_fraction, float(((peaks-values)/peaks).max()))
        check(row.max_drawdown_usd_so_far, max_dd_usd, 'daily cumulative dollar DD')
        check(row.max_drawdown_pct_so_far, max_dd_fraction, 'daily cumulative percent DD', 1e-10, False)
        peak = max(peak, float(values.max())); capital = balance; total_net += day_net
        curve_chunks.append(values); time_chunks.append(clocks)

    check(summary['final_equity'], capital, 'summary final equity')
    check(summary['net_pnl'], total_net, 'summary net P&L')
    check(summary['max_drawdown_usd'], max_dd_usd, 'summary dollar DD')
    check(summary['max_drawdown_pct'], max_dd_fraction*100, 'summary percent DD', 1e-8, False)
    curve = np.concatenate(curve_chunks); times = np.concatenate(time_chunks)
    result = {key: summary.get(key) for key in ['instrument', 'period', 'execution', 'leverage_cap', 'slippage', 'label']}
    result.update(status='passed', sessions=len(daily), trades=len(trades), final_equity=capital,
                  net_pnl=total_net, max_drawdown_usd=max_dd_usd, max_drawdown_pct=max_dd_fraction*100,
                  holding_minutes=holding_minutes,
                  effective_leverage_held_minute_mean=(leverage_sum/holding_minutes if holding_minutes else 0.)
                  if not invalid_weighted_marks else None,
                  effective_leverage_max=max_leverage if not invalid_leverage_marks else None,
                  effective_leverage_max_time=max_leverage_time, effective_leverage_max_mark=max_leverage_kind,
                  nonpositive_equity_leverage_marks=invalid_leverage_marks,
                  max_abs_ledger_error_usd=max(errors, default=0.), reconciliation_checks=len(errors),
                  marks=len(curve), first_mark_time=timestamp(times[0]), last_mark_time=timestamp(times[-1]))
    for name, percentage in [('drawdown_pct', True), ('drawdown_usd', False)]:
        result.update({f'{name}_{key}': value for key, value in drawdown_episode(curve, times, percentage).items()})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=Path('results/2026-10-19'))
    parser.add_argument('--prepared', type=Path, default=Path('data/prepared'))
    parser.add_argument('--out', type=Path, help='Separate audit output folder; defaults to --results.')
    args = parser.parse_args()
    assert args.results.is_dir(), f'missing results folder: {args.results}'
    validation_path = args.prepared/'DATA_VALIDATION.json'
    validation = json.loads(validation_path.read_text(encoding='utf-8'))
    assert validation['status'] == 'passed', 'prepared data validation has not passed'
    expected_hashes = validation['prepared_files_sha256']
    markets = {}; source_hashes = {}; rows = []; skipped = []
    folders = sorted(path for path in args.results.rglob('*_principal') if path.is_dir())
    if args.results.name.endswith('_principal'):
        folders.insert(0, args.results)
    for folder in folders:
        summary_path = folder/'summary.json'
        required = [folder/'trades.csv', folder/'daily.csv', summary_path]
        if not all(path.is_file() for path in required):
            skipped.append(dict(folder=str(folder.resolve()), reason='incomplete scenario files'))
            continue
        summary = json.loads(summary_path.read_text(encoding='utf-8'))
        if summary.get('kind') != 'principal' or float(summary['slippage']) != .001:
            continue
        symbol = summary['instrument']
        if symbol not in markets:
            cache = args.prepared/f'{symbol}_market.pkl'
            actual = digest(cache)
            assert actual == expected_hashes[cache.name], f'prepared cache hash mismatch: {cache}'
            with cache.open('rb') as stream:
                markets[symbol] = pickle.load(stream)
            source_hashes[str(cache.resolve())] = actual
        hashes = {str(path.resolve()): digest(path) for path in required}
        trades = pd.read_csv(folder/'trades.csv', float_precision='round_trip')
        daily = pd.read_csv(folder/'daily.csv', float_precision='round_trip')
        row = audit_frames(markets[symbol], trades, daily, summary)
        row['scenario_folder'] = str(folder.resolve())
        assert all(digest(path) == hashes[str(path.resolve())] for path in required), 'scenario changed during audit'
        rows.append(row); source_hashes.update(hashes)
        print(f'{len(rows):02d} {symbol} {summary["label"]}: ledger/DD OK, max leverage={row["effective_leverage_max"]:.6f}', flush=True)
    assert rows, 'no completed principal scenario at slippage .001 found'
    out = args.out or args.results
    out.mkdir(parents=True, exist_ok=True)
    document = dict(status='passed', utc=datetime.now(timezone.utc).isoformat(), scenarios=len(rows),
                    script_sha256=digest(__file__), data_validation_sha256=digest(validation_path),
                    results=str(args.results.resolve()), prepared=str(args.prepared.resolve()),
                    method=dict(account_marks='Held minute closes, entry reference after costs, exit balance after costs; flat marks retained.',
                                drawdown_duration='Last equal high-water mark before trough to first recovery; otherwise censored at last mark. USD and percentage episodes reported separately.',
                                duration_units='Fractional elapsed calendar days plus integer difference of New York calendar dates.',
                                leverage_mean='Mean exposure/equity at right endpoints of each held minute; executions have zero time weight.',
                                leverage_max='Held minute closes plus entry reference after cost, entry fill after commission, exit reference and fill before closing costs.',
                                costs='Adverse fills and commissions independently recomputed; one day/360 short borrow per trade, charged at exit.',
                                limitation='Minute resolution and simulated execution prices only; no intrabar extrema, ticks, margin liquidation, or true intraminute leverage.',
                                usd_tolerance=USD_TOLERANCE, percent_dd_tolerance_points=1e-8),
                    source_files_sha256=source_hashes, skipped=skipped, results_by_scenario=rows)
    pd.DataFrame(rows).to_csv(out/'INTRADAY_RISK_AUDIT.csv', index=False)
    (out/'INTRADAY_RISK_AUDIT.json').write_text(json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    print(f'PASS: {len(rows)} archived scenarios independently reconciled; no strategy replay.', flush=True)


if __name__ == '__main__':
    main()
