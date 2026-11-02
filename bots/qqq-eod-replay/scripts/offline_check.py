"""Retrospective technical check on one hash-verified existing SIP session."""
from pathlib import Path
from types import SimpleNamespace
import sys,json,hashlib,pickle,argparse,tempfile
import pandas as pd
BOT=Path(__file__).resolve().parents[1];REPO=BOT.parents[1];sys.path.insert(0,str(BOT))
from qqq_eod.source import freeze_sources,activate_sources
from qqq_eod import replay

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--risk',action='store_true');args=p.parse_args()
 lock=json.loads((BOT/'ENGINE_LOCK.json').read_text());prepared=REPO/'studies/intraday-momentum-noise-area/data/prepared';path=prepared/'QQQ_market.pkl'
 digest=hashlib.sha256(path.read_bytes()).hexdigest()
 if digest!='67e5ae72288b8878777683c67343174491895b6069c41f331b13aff422e06711':raise ValueError('untrusted prepared pickle; not loaded')
 with tempfile.TemporaryDirectory(prefix='qqq-eod-realcheck-') as work:
  activate_sources(freeze_sources(REPO,lock,Path(work)/'source'),lock)
  from qqq_paper.strategy import Session
  from orb.engine import trade_path,Config
  with path.open('rb') as f:m=pickle.load(f)
  i=len(m.dates)-1;day=str(m.dates[i].date());opening=pd.Timestamp(day+' 09:30',tz='America/New_York');session=Session(opening,opening+pd.Timedelta(minutes=int(m.lengths[i])))
  bars=pd.DataFrame({k:v[i,:int(m.lengths[i])] for k,v in m.arrays.items()},index=pd.date_range(session.open,session.close,inclusive='left',freq='min'))
  history=SimpleNamespace(dates=m.dates[:i],arrays={k:v[:i] for k,v in m.arrays.items()},lengths=m.lengths[:i],valid=m.valid[:i])
  reference=REPO/'studies/intraday-momentum-noise-area/results/2026-10-19/QQQ/B_next_open_L4_s0.01_principal/daily.csv';daily=pd.read_csv(reference);r=daily[daily.date==day].iloc[0];capital=float(r.equity-r.net_pnl)
  cash=json.loads((prepared/'QQQ_dividends.json').read_text());a=replay.noise(history,bars,session,capital,cash.get(day,0.));b=replay.orb(bars,session,100000)
  if a['status']!='complete' or b['status']!='complete':raise AssertionError('real session unresolved')
  error=abs(a['net_pnl']-float(r.net_pnl))
  if error>1e-6:raise AssertionError('noise historical P&L mismatch')
  differences={}
  for t in b['trades']:
   direct=trade_path(m,i,t['sign'],t['quantity'],Config())
   for field in ('net_pnl','entry_price','exit_price','commission','borrow_fee'):
    delta=abs(t[field]-direct[field]);differences[field]=delta
    if delta>1e-6:raise AssertionError('ORB frozen direct path mismatch')
  result=dict(status='passed',kind='retrospective_technical_only',statistical_sessions=0,day=day,source='existing Alpaca SIP raw prepared archive',market_sha256=digest,strategy_commit=lock['strategy_commit'],noise=dict(status=a['status'],decisions=len(a['decisions']),fills=len(a['fills']),max_pnl_error_usd=error),orb=dict(status=b['status'],trades=len(b['trades']),direct_path_differences=differences),operationally_observed=False,provider_requests=0,broker_orders=0)
  if args.risk:
   from noise_area.features import compute_features
   from noise_area.engine import simulate,Config as NoiseConfig
   from qqq_eod.risk_marks import path_summary
   original=simulate(m,compute_features(m,cash,14),NoiseConfig(slippage=.01),day,day);row=original.daily.iloc[0]
   observed=replay.noise(history,bars,session,100000,cash.get(day,0.))
   expected=dict(minimum=float(row.min_equity),maximum=float(row.max_equity),ending=float(row.equity),within_drawdown_fraction=original.summary['max_drawdown_pct'])
   risk_errors={k:abs(observed['risk'][k]-v) for k,v in expected.items()}
   if max(risk_errors.values())>1e-6:raise AssertionError('Noise risk telemetry differs from frozen original')
   if b['trades']:
    t=b['trades'][0];expected=path_summary([100000+x for x in trade_path(m,i,t['sign'],t['quantity'],Config())['equity_offsets']]);orb_errors={k:abs(b['risk'][k]-expected[k]) for k in ('minimum','maximum','ending','within_drawdown_fraction')}
    if max(orb_errors.values())>1e-6:raise AssertionError('ORB risk telemetry differs from frozen original')
   else:orb_errors={}
   result['risk_telemetry_parity']=dict(noise=risk_errors,orb=orb_errors)
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
