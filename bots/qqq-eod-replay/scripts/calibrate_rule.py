"""Rebuild only the registered frozen baseline and fixed stopping thresholds."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,pickle,hashlib,argparse,subprocess
import numpy as np
import pandas as pd
BOT=Path(__file__).resolve().parents[1];REPO=BOT.parents[1];sys.path.insert(0,str(BOT))
from qqq_eod.source import freeze_sources,activate_sources
from qqq_eod.calibration import bootstrap_bands

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=BOT/'rules/v1');args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
 if (out/'RULE.json').exists():raise ValueError('numeric rule overwrite refused')
 plan_path=BOT/'rules/v1/CALIBRATION_PLAN.json';plan=json.loads(plan_path.read_text(encoding='utf-8'));lock=json.loads((BOT/'ENGINE_LOCK.json').read_text())
 for name,sha in plan['input_sha256'].items():
  if digest(REPO/name)!=sha:raise ValueError('registered calibration input changed')
 if plan['strategy_commit']!=lock['strategy_commit']:raise ValueError('strategy mismatch')
 activate_sources(freeze_sources(REPO,lock,BOT/'runtime/rule7-sources'),lock)
 from noise_area.features import compute_features
 from noise_area.engine import simulate as noise_sim,Config as NoiseConfig
 from orb.engine import simulate as orb_sim,Config as OrbConfig
 prepared=REPO/'studies/intraday-momentum-noise-area/data/prepared'
 with (prepared/'QQQ_market.pkl').open('rb') as stream:market=pickle.load(stream)
 dividends=json.loads((prepared/'QQQ_dividends.json').read_text());nconfig=dict(plan['baseline']['noise']);lookback=nconfig.pop('lookback');first,last=plan['baseline']['period']
 noise=noise_sim(market,compute_features(market,dividends,lookback),NoiseConfig(**nconfig),first,last)
 orb=orb_sim(market,OrbConfig(**plan['baseline']['orb']),first,last)
 # Independent published outputs at the same initial capital: all A for Noise, all ALL for ORB.
 references={'noise':REPO/'studies/intraday-momentum-noise-area/results/2026-10-19/QQQ/A_next_open_L4_s0.01_principal/daily.csv','orb':REPO/'studies/opening-range-5m/results/2026-10-20/QQQ_ALL_both_complete_days_stop_first_s0.01/daily.csv'}
 checks={};rules={}
 for name,result in [('noise',noise),('orb',orb)]:
  frame=result.daily.copy();reference=pd.read_csv(references[name]);merged=frame.merge(reference,on='date',suffixes=('_actual','_published'))
  errors={k:float(np.max(np.abs(merged[k+'_actual']-merged[k+'_published']))) for k in ('net_pnl','equity','quantity','commission','borrow_fee')}
  if len(merged)!=len(reference) or max(errors.values())>1e-6:raise AssertionError('frozen published baseline mismatch')
  checks[name]=dict(reference=references[name].relative_to(REPO).as_posix(),sha256=digest(references[name]),rows=len(merged),max_absolute_errors=errors)
  eligible=frame['eligibility'].eq('eligible').to_numpy() if name=='noise' else ~frame['conditionally_excluded'].to_numpy(dtype=bool)
  returns=frame['return_net'].to_numpy(dtype=float)
  bs=plan['bootstrap'];band=bootstrap_bands(pd.DatetimeIndex(frame.date),returns,eligible,replications=bs['replications'],seed=bs['seed'],length=bs['block_sessions'],horizons=bs['horizons'],initial=bs['initial_capital'])
  historical_dd=float(result.summary['max_drawdown_pct']) if name=='noise' else float(result.observed_close_drawdown_pct)/100
  frame['bootstrap_eligible']=eligible;frame.to_csv(out/(name+'_baseline_daily.csv'),index=False,float_format='%.17g',lineterminator='\n')
  rules[name]=dict(**band,baseline_rows=len(frame),excluded_or_unavailable=int((~eligible).sum()),first_session=str(frame.date.iloc[0]),first_eligible_session=str(frame.loc[eligible,'date'].iloc[0]),last_session=str(frame.date.iloc[-1]),historical_max_drawdown_fraction=historical_dd,stop_drawdown_fraction=historical_dd*plan['stops']['drawdown_multiplier'],baseline_csv_sha256=digest(out/(name+'_baseline_daily.csv')),historical_net_pnl=float(frame.net_pnl.sum()),historical_trades=int(frame.trades.sum()))
  print(json.dumps(dict(bot=name,eligible=int(eligible.sum()),blocks=band['valid_blocks'],bands=band['bands'],drawdown_stop_fraction=rules[name]['stop_drawdown_fraction'])),flush=True)
 rule=dict(schema=1,name='qqq-frozen-stop-v1',strategy_commit=plan['strategy_commit'],calibration_recipe_commit='d21b3e6976ed4d7318d237e9f9998f22cfe25417',calibration_recipe_sha256=digest(plan_path),costs=plan['costs'],model_parameters=plan['baseline'],bootstrap=plan['bootstrap'],stops=plan['stops'],parity=plan['parity'],initial_capital=100000.,bots=rules)
 (out/'RULE.json').write_text(json.dumps(rule,indent=2,allow_nan=False),encoding='utf-8')
 receipt=dict(calculated_utc=datetime.now(timezone.utc).isoformat(),strategy_commit=plan['strategy_commit'],recipe_commit=rule['calibration_recipe_commit'],input_sha256=plan['input_sha256'],script_sha256=digest(__file__),rule_sha256=digest(out/'RULE.json'),published_output_parity=checks,provider_requests=0,broker_orders=0,legacy_live_read=False)
 (out/'calibration_receipt.json').write_text(json.dumps(receipt,indent=2,allow_nan=False),encoding='utf-8');return 0
if __name__=='__main__':raise SystemExit(main())
