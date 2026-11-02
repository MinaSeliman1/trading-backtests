from copy import deepcopy
import pandas as pd
import pytest
from qqq_eod.schedule import calendar

def rule():return dict(schema=1,strategy_commit='frozen',initial_capital=100000.,stops=dict(roundoff_usd=1e-6,roundoff_dd_fraction=1e-10),bots={b:dict(bands={'20':{'p05':-1000},'60':{'p05':-2000}},stop_drawdown_fraction=.2) for b in ('noise','orb')},parity=dict(pnl_or_cost_usd=.01,price_or_feature_absolute=.000001,quantity=0,direction=0,economic_time_seconds=0))
def rows(n=20,bot='noise',last=100000):
 dates=calendar('2026-11-02','2027-03-01').sessions_in_range('2026-11-02','2027-03-01');out=[];before=100000
 for i in range(n):
  after=last if i==n-1 else 100000;out.append(dict(bot=bot,day=str(dates[i].date()),status='complete',result=dict(status='complete',capital_before=before,capital_after=after,net_pnl=after-before,risk=dict(minimum=min(before,after),maximum=max(before,after),ending=after,within_drawdown_fraction=max(0,1-after/before),metric='ordered_minute_close_and_fill_marks'))));before=after
 return out

def test_only_fixed_checkpoints_and_strict_boundary_then_irreversible_stop():
 from qqq_eod.risk_policy import evaluate
 assert not evaluate(rule(),'noise',rows(19,last=98000),'2026-11-02')['stop']
 assert not evaluate(rule(),'noise',rows(20,last=99000),'2026-11-02')['stop']
 past=rows(25);bad=rows(20,last=98999);past[19]=bad[-1];past[20]['result'].update(capital_before=98999,net_pnl=1001)
 x=evaluate(rule(),'noise',past,'2026-11-02');assert x['stop'] and x['trigger_day']==past[19]['day'] and x['reason']=='pnl_below_p5_20'
 assert not evaluate(rule(),'orb',past,'2026-11-02')['stop']

def test_drawdown_uses_intraday_running_peak_not_daily_pnl():
 from qqq_eod.risk_policy import evaluate
 history=rows(1);history[0]['result']['risk']=dict(minimum=90000,maximum=120000,ending=100000,within_drawdown_fraction=.25,metric='ordered_minute_close_and_fill_marks')
 out=evaluate(rule(),'noise',history,'2026-11-02');assert out['stop'] and out['reason']=='drawdown_above_limit'
 history[0]['result']['risk'].update(minimum=100000,maximum=125000,within_drawdown_fraction=.2)
 assert not evaluate(rule(),'noise',history,'2026-11-02')['stop']

def test_unknown_missing_date_or_missing_risk_is_never_promoted_to_cash():
 from qqq_eod.risk_policy import evaluate
 h=rows(20,last=98999);h[3]['status']='unresolved';h[3]['result']['net_pnl']=None
 x=evaluate(rule(),'noise',h,'2026-11-02');assert not x['stop'] and x['resolved_sessions']==3
 h=rows(20);del h[3];assert evaluate(rule(),'noise',h,'2026-11-02')['data_blocked']
 h=rows(1);h[0]['result'].pop('risk');assert evaluate(rule(),'noise',h,'2026-11-02')['data_blocked']

def test_sixty_session_checkpoint_does_not_reset_at_twenty():
 from qqq_eod.risk_policy import evaluate
 h=rows(60,last=97999);x=evaluate(rule(),'noise',h,'2026-11-02');assert x['stop'] and x['reason']=='pnl_below_p5_60'
 legacy=rows(1);legacy[0]['day']='2026-10-30';legacy[0]['result']['capital_after']=0
 assert evaluate(rule(),'noise',legacy+rows(20),'2026-11-02')['resolved_sessions']==20

def test_parity_thresholds_and_unknown_context_are_not_false_agreement():
 from qqq_eod.risk_policy import assess_parity
 x=dict(context=[],differences=[dict(field='net_pnl',statistical=1.,operational=.99)])
 assert not assess_parity(x,rule())['investigate']
 x['differences'][0]['operational']=.98;assert assess_parity(x,rule())['investigate']
 for field,u,v in [('quantity',10,11),('trades.entry_time','2026-11-02T09:35:00-05:00','2026-11-02T09:36:00-05:00'),('price',100,100.01)]:
  assert assess_parity(dict(context=[],differences=[dict(field=field,statistical=u,operational=v)]),rule())['investigate']
 assert assess_parity(dict(context=['live_full_input_version_unverified'],differences=[]),rule())['classification']=='comparison_limited'

def test_publication_requires_the_actual_main_rule_sha_before_first_date():
 from qqq_eod.risk_policy import Policy
 r=dict(head_sha='a'*40,head_branch='main',event='push',repository={'full_name':'MinaSeliman1/trading-backtests'},created_at='2026-11-02T04:59:00Z')
 class Read:
  def get_json(self,path):assert path.endswith('/123');return r
 p=Policy(rule(),'2026-11-02',dict(publication_run_id=123,rule_commit='a'*40));p.verify_publication(Read())
 r['created_at']='2026-11-02T05:00:00Z'
 with pytest.raises(ValueError):p.verify_publication(Read())
 r['created_at']='2026-11-02T04:59:00Z';r['head_sha']='b'*40
 with pytest.raises(ValueError):p.verify_publication(Read())

def test_committed_rule_load_rejects_edit_date_or_model_change(tmp_path,pinned_sources):
 from qqq_eod.risk_policy import load_policy
 from pathlib import Path
 import json,subprocess,hashlib,os
 source=Path(__file__).resolve().parents[1];recipe=json.loads((source/'rules/v1/CALIBRATION_PLAN.json').read_text());numeric=json.loads((source/'rules/v1/RULE.json').read_text())
 folder=tmp_path/'rules/v1';folder.mkdir(parents=True);recipe_raw=json.dumps(recipe).encode();(folder/'CALIBRATION_PLAN.json').write_bytes(recipe_raw)
 env=dict(os.environ,GIT_AUTHOR_DATE='2026-11-01T21:00:00-05:00',GIT_COMMITTER_DATE='2026-11-01T21:00:00-05:00')
 def git(*args):return subprocess.check_output(['git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid',*args],cwd=tmp_path,env=env,text=True).strip()
 git('init');git('add','.');git('commit','-m','Recipe');numeric['calibration_recipe_commit']=git('rev-parse','HEAD');numeric['calibration_recipe_sha256']=hashlib.sha256(recipe_raw).hexdigest();(folder/'RULE.json').write_bytes(json.dumps(numeric).encode());git('add','.');git('commit','-m','Rule')
 a=dict(rule_path='rules/v1/RULE.json',rule_commit=git('rev-parse','HEAD'),rule_publication_run_id=123,first_statistical_session='2026-11-02');lock={'strategy_commit':recipe['strategy_commit']}
 assert load_policy(tmp_path,a,lock).first_session=='2026-11-02'
 with pytest.raises(ValueError):load_policy(tmp_path,dict(a,first_statistical_session='2026-11-03'),lock)
 with pytest.raises(ValueError):load_policy(tmp_path,a,{'strategy_commit':'b'*40})
 (folder/'RULE.json').write_bytes(b'{}')
 with pytest.raises(ValueError):load_policy(tmp_path,a,lock)
