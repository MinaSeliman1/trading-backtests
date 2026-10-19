"""Contrôles de cohérence des 116 exports ; complément de l'audit source des trades."""
from pathlib import Path
import hashlib
import json
import pandas as pd
import numpy as np


def main():
    out=Path('results/alpaca_sip_long')
    comparison=pd.read_csv(out/'comparison_all.csv')
    assert len(comparison)==116 and comparison.label.is_unique
    manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    for path,expected in manifest['source_hashes'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==expected, path
    for source in manifest['inputs']:
        assert hashlib.sha256(Path(source['path']).read_bytes()).hexdigest()==source['sha256']
    original=json.loads((out/'ORIGINAL_PRE_EXECUTION_SPLIT.json').read_text())
    assert original==json.loads((out/'PRE_EXECUTION_SPLIT.json').read_text()), 'split changed after first execution'
    checks=[]
    for _,row in comparison.iterrows():
        folder=out/row.instrument/row.label
        summary=json.loads((folder/'summary.json').read_text())
        trades=pd.read_csv(folder/'trades.csv'); daily=pd.read_csv(folder/'daily.csv')
        monthly=pd.read_csv(folder/'monthly.csv')
        assert len(trades)==summary['trades']==row.trades
        assert len(daily)==summary['valid_sessions']==row.valid_sessions
        assert not trades.date.duplicated().any() and not daily.date.duplicated().any()
        net=float(trades.net_pnl.sum())
        for value in [summary['net_pnl'],row.net_pnl,daily.net_pnl.sum(),monthly.net_pnl.sum(),daily.equity.iloc[-1]-100000]:
            assert abs(value-net)<1e-6, (row.label,value,net)
        if len(trades):
            assert np.allclose(trades.gross_pnl-trades.fees,trades.net_pnl,rtol=0,atol=1e-6)
            assert np.allclose(trades.result_r,trades.net_pnl/trades.initial_risk_usd,rtol=0,atol=1e-6)
            assert (trades.quantity>=1).all() and (trades.quantity%1==0).all()
            entry=pd.to_datetime(trades.entry_time,utc=True).dt.tz_convert('America/New_York')
            exit_times=pd.to_datetime(trades.exit_time,utc=True).dt.tz_convert('America/New_York')
            assert (entry.dt.date==exit_times.dt.date).all()
            assert (entry.dt.strftime('%H:%M')<'11:00').all()
            assert (entry.dt.strftime('%H:%M')>='09:35').all()
            previous=100000+trades.net_pnl.cumsum().shift(1,fill_value=0)
            assert (trades.estimated_loss_at_order_usd<=previous*.005+1e-6).all()
        for grouping in ['direction','entry_hour','volatility_regime']:
            grouped=pd.read_csv(folder/f'by_{grouping}.csv')
            assert int(grouped.trades.sum())==len(trades)
            assert abs(float(grouped.net_pnl.sum())-net)<1e-6
        for bootstrap in ['bootstrap_iid','bootstrap_block5']:
            result=summary[bootstrap]
            if result['status']=='computed':
                assert result['repetitions']==5000 and result['seed']==20261019
                low,high=result['expectancy_r_ci95']
                assert np.isfinite([low,high]).all() and low<=high
        checks.append(dict(label=row.label,trades=len(trades),net_pnl=net))
    for symbol in ['SPY','QQQ']:
        principal=comparison[(comparison.instrument==symbol)&(comparison.test=='principal')]
        assert len(principal)==16
        for segment in ['IS','OOS']:
            part=comparison[(comparison.instrument==symbol)&(comparison.segment==segment)]
            assert len(part)==18
            assert sorted(part.slippage_ticks.unique())==[1,2,3,5]
        for stop in ['A','B']:
            wf=comparison[(comparison.instrument==symbol)&(comparison.segment=='WF_OOS')&(comparison.stop_variant==stop)].sort_values('first_session')
            assert len(wf)==11
            assert all(a<b for a,b in zip(wf.last_session.iloc[:-1],wf.first_session.iloc[1:]))
            assert (wf.training_last<wf.first_session).all()
    figures=json.loads((out/'FIGURES_PROVENANCE.json').read_text())
    assert figures['refreshed_diagnostics']==116 and figures['summary_figures']==6
    assert len(figures['figures'])==122
    for path,expected in figures['figures'].items():
        content=(out/path).read_bytes()
        assert content.startswith(b'\x89PNG\r\n\x1a\n') and len(content)>10000
        assert hashlib.sha256(content).hexdigest()==expected
    audit=json.loads((out/'audit_validation.json').read_text())
    assert audit['status']=='passed'
    checked_primary=comparison[(comparison.test=='principal')&(comparison.slippage_ticks==1)]
    assert audit['trades_checked']==int(checked_primary.trades.sum())
    result=dict(status='passed',verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                scenarios_checked=len(checks),png_files_checked=122,
                code_and_data_hashes_match=True,original_split_unchanged=True,
                scope='All export totals and invariants; detailed source/exit audit covers principal IS/OOS 1-tick trades',
                checks=checks)
    (out/'OUTPUT_VALIDATION.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(f"PASS: {len(checks)} scénarios, 122 PNG, dates initiales et hashes, totaux et invariants rapprochés.")


if __name__=='__main__': main()
