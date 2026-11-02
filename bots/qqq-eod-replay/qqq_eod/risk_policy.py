"""Immutable task7 rules; pure decisions over the new statistical ledger only."""
from pathlib import Path
from dataclasses import dataclass
import json,hashlib,subprocess,re,math
import pandas as pd
from .schedule import calendar
from .risk_marks import extend_peak

def first_after_commit(repo,commit):
 if not re.fullmatch('[0-9a-f]{40}',commit or ''):raise ValueError('full rule commit required')
 stamp=subprocess.check_output(['git','show','-s','--format=%cI',commit],cwd=repo,text=True).strip();day=pd.Timestamp(stamp).tz_convert('America/New_York').date();c=calendar(str(day),str(day))
 return str(next(d.date() for d in c.sessions if d.date()>day))

def evaluate(rule,bot,sessions,first_day):
 if bot not in rule['bots']:raise ValueError('unknown policy account')
 config=rule['bots'][bot];peak=capital=float(rule['initial_capital']);drawdown=0.;count=0;checks=[]
 out=dict(stop=False,data_blocked=False,reason=None,trigger_day=None,resolved_sessions=0,peak=peak,max_drawdown_fraction=0.,checkpoints=checks)
 rows=sorted((r for r in sessions if r['bot']==bot and r['day']>=first_day),key=lambda r:r['day'])
 expected=None
 if rows:expected=iter(calendar(first_day,rows[-1]['day']).sessions_in_range(first_day,rows[-1]['day']))
 for row in rows:
  day=str(next(expected).date())
  if row['day']!=day:out.update(data_blocked=True,reason='missing_calendar_session',trigger_day=day);return out
  if row['status']!='complete':out['pending_day']=day;return out
  result=row.get('result') or {};risk=result.get('risk')
  if result.get('reason')=='registered_risk_stop' or risk is None:out.update(data_blocked=True,reason='missing_or_inconsistent_risk_path',trigger_day=day);return out
  try:
   if risk.get('metric')!='ordered_minute_close_and_fill_marks' or not all(math.isfinite(float(risk[k])) for k in ('minimum','maximum','ending','within_drawdown_fraction')):raise ValueError('risk metric')
   if abs(result['capital_before']-capital)>1e-6 or abs(risk['ending']-result['capital_after'])>1e-6 or not risk['minimum']<=risk['ending']<=risk['maximum'] or risk['within_drawdown_fraction']<0:raise ValueError('risk accounting')
  except (KeyError,TypeError,ValueError):out.update(data_blocked=True,reason='invalid_risk_path',trigger_day=day);return out
  step=extend_peak(peak,risk);peak=step['peak'];drawdown=max(drawdown,step['max_drawdown_fraction']);capital=result['capital_after'];count+=1
  out.update(resolved_sessions=count,peak=peak,max_drawdown_fraction=drawdown)
  if drawdown>config['stop_drawdown_fraction']+rule['stops']['roundoff_dd_fraction']:out.update(stop=True,reason='drawdown_above_limit',trigger_day=day);return out
  if str(count) in config['bands']:
   net=capital-rule['initial_capital'];limit=config['bands'][str(count)]['p05'];checks.append(dict(sessions=count,day=day,net_pnl=net,p05=limit))
   if net<limit-rule['stops']['roundoff_usd']:out.update(stop=True,reason='pnl_below_p5_'+str(count),trigger_day=day);return out
 return out

def assess_parity(comparison,rule):
 reasons=[];epsilon=rule['stops']['roundoff_usd']
 if any(c in comparison.get('context',[]) for c in ('different_archived_price_prefix','source_conflict')):reasons.append(dict(field='source_provenance',context=comparison['context']))
 for item in comparison.get('differences',[]):
  field=item['field'];leaf=field.split('.')[-1];a=item.get('statistical');b=item.get('operational');exceeded=False
  if a is None or b is None:reasons.append(item);continue
  if leaf in ('entry_time','exit_time','timestamp'):exceeded=pd.Timestamp(a)!=pd.Timestamp(b)
  elif leaf in ('quantity','qty','target','sign','direction','decision_count','fills_count','trades_count','exit_reason'):exceeded=a!=b
  else:
   threshold=rule['parity']['pnl_or_cost_usd'] if leaf in ('net_pnl','commission','borrow','borrow_fee','realized') else rule['parity']['price_or_feature_absolute']
   exceeded=abs(float(a)-float(b))>threshold+(epsilon if threshold==rule['parity']['pnl_or_cost_usd'] else 1e-12)
  if exceeded:reasons.append(item)
 return dict(investigate=bool(reasons),classification='investigate' if reasons else 'comparison_limited' if comparison.get('context') else 'within_registered_tolerances',triggers=reasons,context=comparison.get('context',[]),automatic_real_trading=False)

@dataclass(frozen=True)
class Policy:
 rule:dict
 first_session:str
 identity:dict
 def decision(self,bot,journal):return evaluate(self.rule,bot,journal.export()['sessions'],self.first_session)
 def stopped(self,bot,journal):return self.decision(bot,journal)['stop']
 def blocked(self,bot,journal):return self.decision(bot,journal)['data_blocked']
 def verify_publication(self,reader):
  r=reader.get_json('/repos/MinaSeliman1/trading-backtests/actions/runs/'+str(self.identity['publication_run_id']))
  deadline=pd.Timestamp(self.first_session,tz='America/New_York')
  if r.get('head_sha')!=self.identity['rule_commit'] or r.get('head_branch')!='main' or r.get('event') not in ('push','workflow_dispatch') or r.get('repository',{}).get('full_name')!='MinaSeliman1/trading-backtests' or pd.Timestamp(r['created_at'])>=deadline:raise ValueError('rule not proven published before first date')

def load_policy(repo,activation,engine_lock):
 repo=Path(repo).resolve();relative=activation.get('rule_path');commit=activation.get('rule_commit')
 if not relative or not re.fullmatch('[0-9a-f]{40}',commit or ''):raise ValueError('committed rule identity required')
 path=(repo/relative).resolve()
 if not path.is_relative_to(repo):raise ValueError('rule outside repository')
 raw=subprocess.check_output(['git','show',commit+':'+path.relative_to(repo).as_posix()],cwd=repo)
 if raw!=path.read_bytes():raise ValueError('registered numeric rule changed')
 rule=json.loads(raw);first=first_after_commit(repo,commit)
 if rule['strategy_commit']!=engine_lock['strategy_commit'] or activation.get('first_statistical_session')!=first:raise ValueError('rule strategy/date mismatch')
 # The recipe, including all costs, is itself committed before calibration.
 recipe_path=path.parent/'CALIBRATION_PLAN.json';recipe_raw=subprocess.check_output(['git','show',rule['calibration_recipe_commit']+':'+recipe_path.relative_to(repo).as_posix()],cwd=repo)
 if hashlib.sha256(recipe_raw).hexdigest()!=rule['calibration_recipe_sha256']:raise ValueError('recipe identity mismatch')
 recipe=json.loads(recipe_raw)
 if rule['costs']!=recipe['costs'] or rule['model_parameters']!=recipe['baseline'] or rule['stops']!=recipe['stops'] or rule['parity']!=recipe['parity'] or rule['bootstrap']!=recipe['bootstrap']:raise ValueError('registered conventions changed')
 publication=activation.get('rule_publication_run_id')
 if not isinstance(publication,int) or publication<=0:raise ValueError('GitHub publication receipt required')
 subprocess.run(['git','merge-base','--is-ancestor',rule['calibration_recipe_commit'],commit],cwd=repo,check=True,capture_output=True)
 from dataclasses import asdict
 from qqq_paper.strategy import Parameters
 from orb_shadow.core import PARAMETERS
 current=asdict(Parameters())
 expected_costs=dict(commission_per_share_per_side=current['commission'],minimum_per_order=current['minimum_commission'],slippage_per_share_per_side=current['slippage'],borrow_annual=current['borrow_rate'],borrow_days_base=360,borrow_min_days=1)
 noise_expected=dict(execution='next_open',slippage=current['slippage'],leverage_cap=current['leverage_cap'],frequency=current['frequency'],stop='combined',borrow_rate=current['borrow_rate'],lookback=current['lookback'])
 if rule['costs']!=expected_costs or rule['model_parameters']['orb']!=asdict(PARAMETERS) or rule['model_parameters']['noise']!=noise_expected:raise ValueError('frozen runtime costs/parameters differ')
 identity=dict(strategy_commit=rule['strategy_commit'],rule_commit=commit,rule_sha256=hashlib.sha256(raw).hexdigest(),first_session=first,costs=rule['costs'],publication_run_id=publication)
 return Policy(rule,first,identity)
